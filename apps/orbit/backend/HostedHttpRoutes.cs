public static partial class HostedHttp
{
    public static void Map(WebApplication app)
    {
        app.MapGet("/git/{**path}", Handle).RequireRateLimiting("git");
        app.MapPost("/git/{**path}", Handle).RequireRateLimiting("git");
    }
}
