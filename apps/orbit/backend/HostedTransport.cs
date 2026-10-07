using System.Diagnostics;

public static partial class HostedHttp
{
    public static async Task Transfer(HttpContext c, HostedRepository repo, HostedAccess access, CancellationToken ct)
    {
        using var process = new Process();
        var bodyBytes = await HostedCgi.ReadBounded(c.Request.Body, HostedPolicy.InputLimit, ct);
        var startInfo = HostedHttpStart.Build(repo.Root, access.Project, access.Endpoint, access.Query, c.Request.Method, c.Request.ContentType ?? "", bodyBytes.Length, access.Actor["email"]!.GetValue<string>(), c.Request.Headers["Git-Protocol"].ToString());
        process.StartInfo = startInfo;
        process.Start();

        try
        {
            await Task.WhenAll(
                WriteInput(process.StandardInput.BaseStream, bodyBytes, ct),
                HostedCgi.Forward(process.StandardOutput.BaseStream, c.Response, ct),
                HostedCgi.Drain(process.StandardError.BaseStream, ct),
                process.WaitForExitAsync(ct)
            );
        }
        catch (Exception)
        {
            if (!process.HasExited)
            {
                process.Kill(true);
                await process.WaitForExitAsync(CancellationToken.None);
            }
            throw;
        }

        if (process.ExitCode != 0)
            throw new InvalidOperationException("Process exited with non-zero code.");
    }
}
