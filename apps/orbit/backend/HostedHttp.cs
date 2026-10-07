using System.Text.Json.Nodes;
using Microsoft.AspNetCore.Http.Features;

public sealed record HostedAccess(Guid Project,string Endpoint,string Query,string Service,JsonNode Actor);

public static partial class HostedHttp {
    public static async Task Execute(HttpContext c) {
        c.Response.Headers["Cache-Control"] = "no-store";
        var db = c.RequestServices.GetRequiredService<Store>();
        var repo = c.RequestServices.GetRequiredService<HostedRepository>();
        var access = await Authorize(c, db);
        if (access is null) return;
        if (c.Features.Get<IHttpMaxRequestBodySizeFeature>() is var f && f != null && !f.IsReadOnly)
            f.MaxRequestBodySize = HostedPolicy.InputLimit;
        if (!await repo.Gate.WaitAsync(0, c.RequestAborted)) {
            c.Response.StatusCode = 409; return;
        }
        try {
            await RunWithTimeout(c, repo, access, db);
        } finally {
            repo.Gate.Release();
        }
    }
}
