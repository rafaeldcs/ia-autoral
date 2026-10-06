using System.Diagnostics;
using System.Threading;
using System.Threading.Tasks;

public sealed partial class GitProcess
{
    public async Task<string> Run(string directory, string token, CancellationToken cancel, params string[] args)
    {
        using var cts = CancellationTokenSource.CreateLinkedTokenSource(cancel);
        cts.CancelAfter(TimeSpan.FromSeconds(60));
        using var p = new Process { StartInfo = Start(directory, token, args) };
        p.Start();
        var stdout = Read(p.StandardOutput, cts.Token);
        var stderr = Read(p.StandardError, cts.Token);
        try
        {
            await p.WaitForExitAsync(cts.Token);
            await Task.WhenAll(stdout, stderr);
        }
        catch (OperationCanceledException)
        {
            if (!p.HasExited) p.Kill(true);
            await p.WaitForExitAsync(CancellationToken.None);
            throw new InvalidOperationException("Operação Git cancelada ou excedeu o tempo limite.");
        }
        if (p.ExitCode != 0) throw new InvalidOperationException("Erro no processo Git.");
        return (await stdout).Trim();
    }
}
