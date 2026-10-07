using System.Text;

public static partial class HostedCgi
{
    private static async Task<string> ReadHeader(Stream source, CancellationToken ct)
    {
        var ms = new MemoryStream();
        var buffer = new byte[1];
        try
        {
            while (ms.Length < 8192)
            {
                var read = await source.ReadAsync(buffer, 0, 1, ct);
                if (read == 0) throw new InvalidOperationException();
                ms.Write(buffer, 0, read);
                var buf = ms.GetBuffer();
                if (ms.Length >= 4 && buf[ms.Length - 4] == '\r' && buf[ms.Length - 3] == '\n' && buf[ms.Length - 2] == '\r' && buf[ms.Length - 1] == '\n')
                    return Encoding.ASCII.GetString(ms.ToArray());
                if (ms.Length >= 2 && buf[ms.Length - 2] == '\n' && buf[ms.Length - 1] == '\n')
                    return Encoding.ASCII.GetString(ms.ToArray());
            }
            throw new InvalidOperationException();
        }
        finally
        {
            ms.Dispose();
        }
    }
}
