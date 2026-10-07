using Microsoft.AspNetCore.Http;

public static partial class HostedCgi
{
    public static async Task Forward(Stream source, HttpResponse response, CancellationToken ct)
    {
        var header = await ReadHeader(source, ct);
        ApplyHeaders(header, response);
        var buffer = new byte[16 * 1024];
        long total = 0;
        int read;
        while ((read = await source.ReadAsync(buffer, 0, buffer.Length, ct)) > 0)
        {
            total += read;
            if (total > HostedPolicy.OutputLimit)
                throw new InvalidOperationException("Output limit exceeded.");
            await response.Body.WriteAsync(buffer.AsMemory(0, read), ct);
        }
    }

    public static async Task Drain(Stream stream, CancellationToken ct)
    {

        await ReadBounded(stream, 32768, ct);
    }
}
