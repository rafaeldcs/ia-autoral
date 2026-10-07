using System;
using System.IO;
using System.Threading;
using System.Threading.Tasks;

public static partial class HostedHttp
{
    private static async Task WriteInput(Stream stdin, byte[] body, CancellationToken ct)
    {
        try { await stdin.WriteAsync(body.AsMemory(), ct); } finally { stdin.Close(); }
    }
}
