using Microsoft.AspNetCore.DataProtection;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Routing;
using System.Threading;

public record GitInput(string Url, string Branch, string Workflow, bool AutoDeploy, string? Token);

public static partial class GitEndpoints
{
    private static readonly SemaphoreSlim Gate = new SemaphoreSlim(1, 1);
    private static bool ValidToken(string? token) => token is null || (token.Length <= 256 && token.All(c => c >= 33 && c <= 126));

    public static void MapConfigure(WebApplication app) => app.MapPost("/api/projects/{project:guid}/git", Configure);

    public static void Map(WebApplication app)
    {
        MapRead(app);
        MapConfigure(app);
        MapQueue(app);
    }
}
