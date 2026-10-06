using System.Text.Json;
public sealed partial class GitCheckout
{
    private async Task<string> Commits(string path, string token, CancellationToken cancel)
    {
        var output = await process.Run(path, token, cancel, "log", "-20", "--format=%H%x09%s");
        return JsonSerializer.Serialize(
            output.Split('\n', StringSplitOptions.RemoveEmptyEntries)
                  .Select(line => line.Split('\t', 2))
                  .Select(parts => new { sha = parts[0], subject = parts.Length > 1 ? parts[1].Substring(0, Math.Min(500, parts[1].Length)) : "" })
        );
    }
}
