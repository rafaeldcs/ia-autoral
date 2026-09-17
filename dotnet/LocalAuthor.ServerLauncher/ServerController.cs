using System.Diagnostics;
using System.Net.Http.Headers;
using System.Security.Cryptography;
using System.Text.Json;
using LocalAuthor.Connectivity;

namespace LocalAuthor.ServerLauncher;

internal sealed record ServerState(bool BackendReady, bool NetworkReady, string Message)
{
    public bool Ready => BackendReady && NetworkReady;
}

internal sealed class ServerController
{
    private readonly string dataRoot;
    private readonly string startupScript;
    private static readonly JsonSerializerOptions Json = new() { PropertyNameCaseInsensitive = true };

    public ServerController(string localData)
    {
        dataRoot = Path.Combine(localData, "LocalAuthor", "lan");
        startupScript = Path.Combine(localData, "LocalAuthor", "lan-runtime", "Start-Server.ps1");
    }

    public string LogFolder => dataRoot;

    public void Start()
    {
        if (!File.Exists(Path.Combine(dataRoot, "server.json")) || !File.Exists(startupScript))
            throw new InvalidOperationException("Este computador ainda não foi preparado como servidor. Instale o servidor LocalAuthor primeiro.");

        // The installed supervisor owns the single-instance mutex and preserves running services.
        var command = new ProcessStartInfo(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.System), "WindowsPowerShell", "v1.0", "powershell.exe"))
        {
            UseShellExecute = false,
            CreateNoWindow = true,
            WindowStyle = ProcessWindowStyle.Hidden
        };
        foreach (var argument in new[] { "-NoProfile", "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass", "-File", startupScript, "-Supervise" })
            command.ArgumentList.Add(argument);
        using var process = Process.Start(command) ?? throw new InvalidOperationException("Não foi possível iniciar o supervisor.");
    }

    public async Task<ServerState> CheckAsync(CancellationToken cancellation)
    {
        var file = Path.Combine(dataRoot, "server.json");
        if (!File.Exists(file)) return new(false, false, "Configuração do servidor não encontrada.");
        Configuration config;
        try
        {
            config = JsonSerializer.Deserialize<Configuration>(await File.ReadAllTextAsync(file, cancellation), Json)
                ?? throw new InvalidDataException();
            if (config.BackendPort is < 1024 or > 65535 || config.Port is < 1024 or > 65535 ||
                string.IsNullOrWhiteSpace(config.BackendHome) || !Path.IsPathFullyQualified(config.BackendHome) || config.CertificateSha256?.Length != 64)
                throw new InvalidDataException();
        }
        catch (Exception ex) when (ex is JsonException or IOException or InvalidDataException or ArgumentException or UnauthorizedAccessException)
        {
            return new(false, false, "Não foi possível ler a configuração. Consulte a pasta de diagnóstico.");
        }

        var backendReady = false;
        try
        {
            using var backend = new HttpClient(new HttpClientHandler { UseProxy = false, AllowAutoRedirect = false }) { Timeout = TimeSpan.FromSeconds(3) };
            var token = (await File.ReadAllTextAsync(Path.Combine(config.BackendHome, "api.token"), cancellation)).Trim();
            backend.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", token);
            using var response = await backend.GetAsync($"http://127.0.0.1:{config.BackendPort}/api/health", cancellation);
            if (response.IsSuccessStatusCode)
            {
                using var body = JsonDocument.Parse(await response.Content.ReadAsStringAsync(cancellation));
                backendReady = body.RootElement.TryGetProperty("status", out var status) && status.GetString() == "ok";
            }
        }
        catch (Exception ex) when (ex is HttpRequestException or IOException or JsonException or OperationCanceledException or FormatException or InvalidOperationException or UnauthorizedAccessException) { }
        if (cancellation.IsCancellationRequested) cancellation.ThrowIfCancellationRequested();
        if (!backendReady) return new(false, false, "Aguardando a IA iniciar. Seus projetos e aprendizados serão preservados.");

        var addresses = config.AutoDiscover
            ? LanDiscovery.Interfaces().Select(network => network.Address.ToString()).Distinct().ToArray()
            : new[] { config.Bind };
        if (addresses.Length == 0) return new(true, false, "IA ligada. Conecte este computador à rede local para atender outros computadores.");
        using var handler = new HttpClientHandler { UseProxy = false, AllowAutoRedirect = false };
        handler.ServerCertificateCustomValidationCallback = (_, certificate, _, _) => certificate is not null
            && certificate.NotBefore.ToUniversalTime() <= DateTime.UtcNow
            && certificate.NotAfter.ToUniversalTime() > DateTime.UtcNow
            && string.Equals(certificate.GetCertHashString(HashAlgorithmName.SHA256), config.CertificateSha256, StringComparison.OrdinalIgnoreCase);
        using var gateway = new HttpClient(handler) { Timeout = TimeSpan.FromSeconds(3) };
        foreach (var address in addresses)
        {
            try
            {
                // Public UI asset: confirms pinned HTTPS gateway and its backend, without a device key.
                using var response = await gateway.GetAsync($"https://{address}:{config.Port}/", cancellation);
                if (response.IsSuccessStatusCode)
                    return new(true, true, "A IA e o acesso pela rede estão respondendo neste computador.");
            }
            catch (Exception ex) when (ex is HttpRequestException or OperationCanceledException or UriFormatException) { }
            cancellation.ThrowIfCancellationRequested();
        }
        return new(true, false, "IA ligada. Aguardando o acesso HTTPS da rede; confira a conexão e a pasta de diagnóstico.");
    }

    private sealed record Configuration(string Bind, int Port, int BackendPort, string BackendHome, string CertificateSha256, bool AutoDiscover);
}
