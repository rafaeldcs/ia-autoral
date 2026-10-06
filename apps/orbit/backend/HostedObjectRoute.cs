public sealed record HostedObjectInput(string? Sha, string? Type);

public static partial class HostedEndpoints
{
    private static void MapMore(WebApplication app)
    {
        app.MapGet("/api/projects/{project:guid}/repository/tokens", List);
        app.MapPost("/api/projects/{project:guid}/repository/tokens", CreateToken);
        app.MapPost("/api/projects/{project:guid}/repository/tokens/{id:guid}/revoke", HostedTokens.Revoke);
        app.MapPost("/api/projects/{project:guid}/repository/object", Read);
    }
}
