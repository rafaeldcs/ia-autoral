using Microsoft.AspNetCore.Http;
using System.Threading.Tasks;

public static partial class HostedHttp {
    public static async Task<HostedAccess?> Authorize(HttpContext c, Store db) {
        var route = MatchRoute(c);
        if (route == null || !RequireBody(c, route)) return null;
        var actor = await HostedTokens.Authenticate(db, c.Request.Headers.Authorization.ToString());
        if (actor == null) {
            c.Response.StatusCode = 401;
            c.Response.Headers["WWW-Authenticate"] = "Basic realm=\"Orbit Git\"";
            return null;
        }
        if (Guid.Parse(actor["project_id"]!.GetValue<string>()) != route.Project) {
            c.Response.StatusCode = 403;
            return null;
        }
        if (route.Service == "receive-pack" &&
            (!actor["write_access"]!.GetValue<bool>() || !HostedPolicy.CanWrite(actor["role"]!.GetValue<string>()))) {
            c.Response.StatusCode = 403;
            return null;
        }

        var repo = c.RequestServices.GetRequiredService<HostedRepository>();
        if (!await repo.RepositoryExists(route.Project, db)) {
            c.Response.StatusCode = 404;
            return null;
        }
        return new HostedAccess(route.Project, route.Endpoint, route.Query, route.Service, actor);
    }
}
