using System.Diagnostics;
using System.Security.Cryptography;
using System.Text.Json;
using LocalAuthor.Connectivity;

namespace LocalAuthor.Client;

// Local enrollment uses the current Windows user's server installation, never a LAN advertisement.
internal sealed class LocalServerConnection(string localData, string clientHome)
{
    private readonly string serverHome = Path.Combine(localData, "LocalAuthor", "lan");
    private readonly string supervisor = Path.Combine(localData, "LocalAuthor", "lan-runtime", "Start-Server.ps1");
    private static readonly JsonSerializerOptions Json = new() { PropertyNameCaseInsensitive = true };
    public bool IsConfigured => File.Exists(Path.Combine(serverHome, "server.json"));
    public bool UsingLocalServer { get; private set; }

    internal static Connection? ReadSaved(string home)
    {
        var file = Path.Combine(home, "connection.bin");
        if (!File.Exists(file)) return null;
        var value = Connection.Parse(ProtectedData.Unprotect(File.ReadAllBytes(file), null, DataProtectionScope.CurrentUser));
        value.Validate();
        return value;
    }

    internal static void Save(string home, Connection connection)
    {
        Directory.CreateDirectory(home);
        var pending = Path.Combine(home, Guid.NewGuid().ToString("N") + ".tmp");
        try
        {
            File.WriteAllBytes(pending, ProtectedData.Protect(JsonSerializer.SerializeToUtf8Bytes(connection), null, DataProtectionScope.CurrentUser));
            File.Move(pending, Path.Combine(home, "connection.bin"), true);
        }
        finally { if (File.Exists(pending)) File.Delete(pending); }
    }

    public async Task<Connection?> PrepareAsync(Action<string> progress, CancellationToken cancel)
    {
        UsingLocalServer = false;
        Directory.CreateDirectory(clientHome);
        // Serialize first enrollment across simultaneous startup/desktop launches.
        using var deadline = CancellationTokenSource.CreateLinkedTokenSource(cancel);
        deadline.CancelAfter(TimeSpan.FromSeconds(90));
        FileStream? gate = null;
        while (gate is null)
        {
            deadline.Token.ThrowIfCancellationRequested();
            try { gate = new FileStream(Path.Combine(clientHome, "local-startup.lock"), FileMode.OpenOrCreate, FileAccess.ReadWrite, FileShare.None); }
            catch (IOException) { await Task.Delay(250, deadline.Token); }
        }
        using (gate)
        {
            var saved = ReadSaved(clientHome);
            if (!IsConfigured) return saved;
            var config = JsonSerializer.Deserialize<Configuration>(File.ReadAllText(Path.Combine(serverHome, "server.json")), Json)
                ?? throw new InvalidDataException("Configuração do servidor local ausente.");
            // A connection explicitly paired with another server must remain paired with that server.
            if (saved is not null && !string.Equals(saved.CertificateSha256, config.CertificateSha256, StringComparison.OrdinalIgnoreCase)) return saved;
            if (!File.Exists(supervisor)) throw new FileNotFoundException("Repare a instalação do servidor local: o inicializador está ausente.");
            var endpoint = $"https://{(config.AutoDiscover ? "127.0.0.1" : config.Bind)}:{config.Port}";
            new Connection(endpoint, config.CertificateSha256, new string('A', 64), "", "", config.DiscoveryPort).Validate();
            if (config.Port < 1024 || config.Port > 65535) throw new InvalidDataException("Porta do servidor local inválida.");
            UsingLocalServer = true;
            if (saved is null)
            {
                progress("Preparando o acesso à IA deste computador…");
                var runtime = JsonSerializer.Deserialize<Runtime>(File.ReadAllText(Path.Combine(serverHome, "runtime.json")), Json)
                    ?? throw new InvalidDataException("Instalação do servidor local incompleta.");
                if (!Path.IsPathFullyQualified(runtime.Gateway) || !File.Exists(runtime.Gateway)) throw new FileNotFoundException("Repare a instalação do servidor local: o serviço HTTPS está ausente.");
                // Private temporary enrollment is immediately converted to DPAPI storage, never shown to the user.
                var temporary = Path.Combine(serverHome, "local-" + Guid.NewGuid().ToString("N") + ".localauthor");
                try
                {
                    var start = new ProcessStartInfo(runtime.Gateway) { UseShellExecute = false, CreateNoWindow = true, RedirectStandardOutput = true, RedirectStandardError = true };
                    foreach (var arg in new[] { "add-device", "--data", serverHome, "--name", "IA neste computador", "--output", temporary }) start.ArgumentList.Add(arg);
                    using var process = Process.Start(start) ?? throw new IOException("Não foi possível preparar o acesso local.");
                    var stdout = process.StandardOutput.ReadToEndAsync(cancel);
                    var stderr = process.StandardError.ReadToEndAsync(cancel);
                    try { await process.WaitForExitAsync(deadline.Token); }
                    catch { if (!process.HasExited) process.Kill(true); throw; }
                    await Task.WhenAll(stdout, stderr);
                    if (process.ExitCode != 0) throw new IOException("Não foi possível preparar o acesso local. Consulte o diagnóstico do servidor.");
                    saved = Connection.Import(temporary);
                    if (!string.Equals(saved.CertificateSha256, config.CertificateSha256, StringComparison.OrdinalIgnoreCase)) throw new InvalidDataException("A identidade do servidor local mudou durante a conexão.");
                    Save(clientHome, saved);
                }
                finally { if (File.Exists(temporary)) File.Delete(temporary); }
            }
            saved = saved with { Server = endpoint };
            if (!await ServerLocator.ProbeAsync(saved, cancel))
            {
                progress("Ligando a IA deste computador. Aguarde…");
                var start = new ProcessStartInfo(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.System), "WindowsPowerShell", "v1.0", "powershell.exe"))
                    { UseShellExecute = false, CreateNoWindow = true, WindowStyle = ProcessWindowStyle.Hidden };
                foreach (var arg in new[] { "-NoProfile", "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass", "-File", supervisor, "-Supervise" }) start.ArgumentList.Add(arg);
                using var process = Process.Start(start);
                var until = DateTime.UtcNow.AddSeconds(60);
                while (!await ServerLocator.ProbeAsync(saved, cancel))
                {
                    if (DateTime.UtcNow >= until) throw new HttpRequestException("O servidor local ainda está iniciando. Vou tentar novamente automaticamente.");
                    await Task.Delay(1000, cancel);
                }
            }
            Save(clientHome, saved);
            return saved;
        }
    }

    private sealed record Configuration(string Bind, int Port, string CertificateSha256, bool AutoDiscover = false, int DiscoveryPort = 38443);
    private sealed record Runtime(string Gateway);
}
