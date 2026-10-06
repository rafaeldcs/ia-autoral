public sealed partial class HostedRepository
{
    public async Task<object> ReadObject(Guid project, string sha, string type, CancellationToken ct)
    {
        await VerifyObject(project, sha, type, ct);
        return type == "tree"
            ? new { entries = await Tree(project, sha, ct) }
            : new { text = await ReadBlob(project, sha, ct) };
    }
}
