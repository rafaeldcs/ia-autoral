using System.Text.RegularExpressions;

public sealed record HostedRoute(Guid Project, string Endpoint, string Query, string Service);

public static partial class HostedHttp
{
    private static HostedRoute? MatchRoute(HttpContext c)
    {
        var path = c.Request.Path.ToString();
        var match = Regex.Match(path, @"\A/git/([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})\.git/(info/refs|git-upload-pack|git-receive-pack)\z");
        if (!match.Success) { c.Response.StatusCode = 400; return null; }
        var uuid = Guid.Parse(match.Groups[1].Value);
        var endpoint = match.Groups[2].Value;
        var query = (c.Request.QueryString.Value ?? "").TrimStart('?');
        var service = HostedPolicy.Service(c.Request.Method, endpoint, query);
        if (service is null) { c.Response.StatusCode = 400; return null; } return new HostedRoute(uuid, endpoint, query, service);
    }
}
