using System.Text;

public sealed partial class GitProcess
{
    private static async Task<string> Read(StreamReader reader, CancellationToken ct) {
    var buffer = new char[1024];
    var output = new StringBuilder();
    while (true) {
        int read = await reader.ReadAsync(buffer.AsMemory(), ct);
        if (read <= 0) break;
        int take = Math.Min(read, 32768 - output.Length);
        output.Append(buffer, 0, take);
    }
    return output.ToString();
}

}
