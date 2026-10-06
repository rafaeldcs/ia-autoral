public static partial class HostedHttp {
    public static async Task RunWithTimeout(HttpContext c, HostedRepository repo, HostedAccess access, Store db) {
        using var cts = CancellationTokenSource.CreateLinkedTokenSource(c.RequestAborted);
        var token = cts.Token;
        cts.CancelAfter(TimeSpan.FromSeconds(60));
        await Transfer(c, repo, access, token);
        if (access.Service == "receive-pack")
            await db.Execute("INSERT INTO audit(actor,action) VALUES($1,$2)",
                access.Actor["name"]!.GetValue<string>(),
                "Recebeu uma operação Git no projeto " + access.Project);
    }
}
