public static partial class HostedEndpoints
{
    public static void Map(WebApplication app)
    {
        app.MapGet("/api/projects/{project:guid}/repository", View);
        app.MapPost("/api/projects/{project:guid}/repository", Create);
        MapMore(app);
    }
}
