using Microsoft.AspNetCore.Http;
using System.Text;
public sealed class HostedCgiTests
{
    private static DefaultHttpContext Context(){var c=new DefaultHttpContext();c.Response.Body=new MemoryStream();return c;}
    [Fact]
    public async Task BinaryProtocolBodyIsNotDroppedOrDecodedAsText()
    {
        var body=Enumerable.Range(0,70000).Select(i=>(byte)(i%256)).ToArray();
        using var source=new MemoryStream(Encoding.ASCII.GetBytes("Content-Type: application/x-git-upload-pack-result\r\n\r\n").Concat(body).ToArray());
        var c=Context();await HostedCgi.Forward(source,c.Response,CancellationToken.None);
        Assert.Equal(body,((MemoryStream)c.Response.Body).ToArray());Assert.Equal("application/x-git-upload-pack-result",c.Response.ContentType);
    }
    [Fact]
    public async Task ParsesStatusAndNeverCopiesAuthenticationOrCookies()
    {
        using var source=new MemoryStream(Encoding.ASCII.GetBytes("Status: 403 Forbidden\nContent-Type: text/plain\nSet-Cookie: secret=value\nLocation: https://example.invalid\n\ndenied"));
        var c=Context();await HostedCgi.Forward(source,c.Response,CancellationToken.None);
        Assert.Equal(403,c.Response.StatusCode);Assert.False(c.Response.Headers.ContainsKey("Set-Cookie"));Assert.False(c.Response.Headers.ContainsKey("Location"));
        Assert.Equal("no-store",c.Response.Headers.CacheControl.ToString());Assert.Equal("denied",Encoding.ASCII.GetString(((MemoryStream)c.Response.Body).ToArray()));
    }
    [Fact]
    public async Task HeaderMustBeCompleteAndBounded()
    {
        foreach(var data in new[]{"Content-Type: text/plain\r\n",new string('x',8193)}){
            using var source=new MemoryStream(Encoding.ASCII.GetBytes(data));
            await Assert.ThrowsAsync<InvalidOperationException>(()=>HostedCgi.Forward(source,Context().Response,CancellationToken.None));
        }
    }
    [Fact]
    public async Task InputCannotExceedTheSelectedByteLimit()
    {
        using var allowed=new MemoryStream(new byte[]{1,2,3});Assert.Equal(new byte[]{1,2,3},await HostedCgi.ReadBounded(allowed,3,CancellationToken.None));
        using var exceeded=new MemoryStream(new byte[]{1,2,3,4});await Assert.ThrowsAsync<InvalidOperationException>(()=>HostedCgi.ReadBounded(exceeded,3,CancellationToken.None));
    }
    private sealed class FragmentedStream(byte[] bytes):MemoryStream(bytes)
    {
        public override Task<int> ReadAsync(byte[] buffer,int offset,int count,CancellationToken ct)
            =>base.ReadAsync(buffer,offset,Math.Min(count,1),ct);
        public override ValueTask<int> ReadAsync(Memory<byte> buffer,CancellationToken ct=default)
            =>base.ReadAsync(buffer[..Math.Min(buffer.Length,1)],ct);
    }
    [Fact]
    public async Task FragmentedInputCannotHideTheByteAfterAnExactLimit()
    {
        using var source=new FragmentedStream([1,2,3,4]);
        await Assert.ThrowsAsync<InvalidOperationException>(()=>HostedCgi.ReadBounded(source,3,CancellationToken.None));
    }
    [Fact]
    public async Task StderrMustBeDrainedAndBounded()
    {
        using var source=new MemoryStream(new byte[32769]);
        await Assert.ThrowsAsync<InvalidOperationException>(()=>HostedCgi.Drain(source,CancellationToken.None));
    }
    [Fact]
    public async Task OutputLimitStopsAnOversizedPackResponse()
    {
        using var source=new MemoryStream(Encoding.ASCII.GetBytes("Content-Type: application/x-git-upload-pack-result\n\n").Concat(new byte[HostedPolicy.OutputLimit+1]).ToArray());
        await Assert.ThrowsAsync<InvalidOperationException>(()=>HostedCgi.Forward(source,Context().Response,CancellationToken.None));
    }
}
