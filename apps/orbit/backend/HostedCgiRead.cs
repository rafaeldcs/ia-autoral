public static partial class HostedCgi {
    public static async Task<byte[]> ReadBounded(Stream stream, int limit, CancellationToken ct) {
        using var ms = new MemoryStream();
        var buffer = new byte[8192];
        int accumulated = 0;
        while (true) {
            var read = await stream.ReadAsync(buffer, 0, buffer.Length, ct);
            if (read == 0) break;
            if (accumulated + read > limit) throw new InvalidOperationException();
            ms.Write(buffer, 0, read);
            accumulated += read;
        }
        return ms.ToArray();
    }
}
