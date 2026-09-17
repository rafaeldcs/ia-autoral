using System.Diagnostics;
using System.Text.Json;

namespace LocalAuthor.ServerLauncher;

internal static class Program
{
    [STAThread]
    private static void Main(string[] args)
    {
        ApplicationConfiguration.Initialize();
        var localData = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
        string? report = args.Length == 2 && args[0] == "--smoke" ? Path.GetFullPath(args[1]) : null;
        Application.Run(new ServerWindow(new ServerController(localData), report));
    }
}

internal sealed class ServerWindow : Form
{
    private readonly ServerController controller;
    private readonly string? report;
    private readonly CancellationTokenSource lifetime = new();
    private readonly System.Windows.Forms.Timer timer = new() { Interval = 5000 };
    private readonly Label status = new() { Text = "Ligando o servidor…", AutoSize = true, Font = new Font("Segoe UI", 20, FontStyle.Bold) };
    private readonly Label details = new() { AutoSize = true, MaximumSize = new Size(550, 0), Text = "Isso pode levar alguns instantes." };
    private readonly Label backend = new() { AutoSize = true, Text = "IA local: aguardando" };
    private readonly Label network = new() { AutoSize = true, Text = "Acesso pela rede: aguardando" };
    private readonly Button retry = new() { Text = "Tentar novamente", AutoSize = true, Padding = new Padding(12, 6, 12, 6), Enabled = false };
    private bool checking;
    private DateTime started = DateTime.UtcNow;
    private bool startupFailed;

    public ServerWindow(ServerController controller, string? report)
    {
        this.controller = controller;
        this.report = report;
        Text = "LocalAuthor Servidor";
        ClientSize = new Size(620, 540);
        MinimumSize = new Size(590, 560);
        StartPosition = FormStartPosition.CenterScreen;
        Font = new Font("Segoe UI", 11);
        BackColor = Color.FromArgb(247, 248, 252);
        AutoScaleMode = AutoScaleMode.Dpi;
        var layout = new FlowLayoutPanel { Dock = DockStyle.Fill, FlowDirection = FlowDirection.TopDown, WrapContents = false, Padding = new Padding(26), AutoScroll = true };
        layout.Controls.Add(new Label { Text = "LOCALAUTHOR  /  SERVIDOR", AutoSize = true, ForeColor = Color.FromArgb(91, 76, 185), Margin = new Padding(0, 0, 0, 18) });
        layout.Controls.Add(status);
        details.Margin = new Padding(0, 12, 0, 22);
        layout.Controls.Add(details);
        backend.Margin = network.Margin = new Padding(0, 5, 0, 5);
        layout.Controls.Add(backend);
        layout.Controls.Add(network);
        var actions = new FlowLayoutPanel { AutoSize = true, Margin = new Padding(0, 24, 0, 16) };
        var open = new Button { Text = "Abrir minha IA", AutoSize = true, Padding = new Padding(12, 6, 12, 6) };
        open.Click += (_, _) => OpenClient();
        retry.Click += async (_, _) => { StartSupervisor(); await RefreshAsync(); };
        actions.Controls.Add(open);
        actions.Controls.Add(retry);
        layout.Controls.Add(actions);
        layout.Controls.Add(new Label { Text = "Você pode fechar esta janela: o servidor continua ligado.\nMantenha o computador ligado e conectado à mesma rede dos clientes.", AutoSize = true, MaximumSize = new Size(550, 0), ForeColor = Color.DimGray });
        var logs = new LinkLabel { Text = "Abrir pasta de diagnóstico", AutoSize = true, Margin = new Padding(0, 18, 0, 0) };
        logs.LinkClicked += (_, _) => { if (Directory.Exists(controller.LogFolder)) Process.Start(new ProcessStartInfo("explorer.exe", controller.LogFolder) { UseShellExecute = true }); };
        layout.Controls.Add(logs);
        Controls.Add(layout);
        if (report is not null) { Opacity = 0; ShowInTaskbar = false; }
        Shown += async (_, _) => { StartSupervisor(); await RefreshAsync(); if (!IsDisposed) timer.Start(); };
        timer.Tick += async (_, _) => await RefreshAsync();
        FormClosed += (_, _) => { timer.Stop(); timer.Dispose(); lifetime.Cancel(); };
    }

    private void StartSupervisor()
    {
        started = DateTime.UtcNow;
        startupFailed = false;
        retry.Enabled = false;
        try { controller.Start(); }
        catch (Exception ex) when (ex is IOException or InvalidOperationException or System.ComponentModel.Win32Exception or UnauthorizedAccessException)
        {
            startupFailed = true;
            status.Text = "Não foi possível ligar";
            details.Text = ex is InvalidOperationException ? ex.Message : "Não foi possível abrir o supervisor. Confira a instalação e a pasta de diagnóstico.";
            retry.Enabled = true;
        }
    }

    private async Task RefreshAsync()
    {
        if (checking || IsDisposed) return;
        checking = true;
        try
        {
            ServerState state = startupFailed ? new(false, false, details.Text) : await controller.CheckAsync(lifetime.Token);
            if (IsDisposed) return;
            var timedOut = DateTime.UtcNow - started > TimeSpan.FromSeconds(45);
            status.Text = state.Ready ? "Servidor pronto" : state.BackendReady ? "IA ligada · rede pendente" : startupFailed || timedOut ? "Servidor precisa de atenção" : "Ligando o servidor…";
            status.ForeColor = state.Ready ? Color.FromArgb(27, 119, 80) : Color.FromArgb(72, 65, 105);
            details.Text = timedOut && !state.BackendReady ? "A IA não respondeu em 45 segundos. Consulte a pasta de diagnóstico e tente novamente." : state.Message;
            backend.Text = state.BackendReady ? "✓ IA local respondendo" : "• IA local: aguardando";
            network.Text = state.NetworkReady ? "✓ Servidor HTTPS respondendo" : "• Acesso pela rede: aguardando";
            retry.Enabled = !state.Ready;
            if (report is not null && (state.Ready || timedOut || startupFailed))
            {
                Directory.CreateDirectory(Path.GetDirectoryName(report)!);
                using var bitmap = new Bitmap(Width, Height);
                DrawToBitmap(bitmap, new Rectangle(0, 0, Width, Height));
                bitmap.Save(Path.ChangeExtension(report, ".png"));
                File.WriteAllText(report, JsonSerializer.Serialize(new { success = state.Ready, state.BackendReady, state.NetworkReady, status = status.Text, closesWithoutStoppingServer = true }, new JsonSerializerOptions { WriteIndented = true }));
                Environment.ExitCode = state.Ready ? 0 : 1;
                Close();
            }
        }
        catch (OperationCanceledException) when (lifetime.IsCancellationRequested) { }
        catch (Exception)
        {
            if (!IsDisposed) { status.Text = "Não foi possível verificar"; details.Text = "Consulte a pasta de diagnóstico e tente novamente."; retry.Enabled = true; }
        }
        finally { checking = false; }
    }

    private void OpenClient()
    {
        var client = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Programs", "LocalAuthorClient", "LocalAuthor.Client.exe");
        if (!File.Exists(client)) { MessageBox.Show(this, "Instale o aplicativo LocalAuthor para abrir suas conversas.", "LocalAuthor", MessageBoxButtons.OK, MessageBoxIcon.Information); return; }
        try { Process.Start(new ProcessStartInfo(client) { UseShellExecute = true }); }
        catch (System.ComponentModel.Win32Exception) { MessageBox.Show(this, "Não foi possível abrir o aplicativo LocalAuthor."); }
    }
}
