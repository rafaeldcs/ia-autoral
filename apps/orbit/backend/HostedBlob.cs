public sealed partial class HostedRepository
{
    public async Task<string> ReadBlob(Guid project, string sha, CancellationToken ct)
    {
        var dir = DirectoryFor(project);
        var sizeStr = await git.Run(dir, "", ct, "cat-file", "-s", sha);
        if (!int.TryParse(sizeStr, out var size) || size < 0 || size > HostedPolicy.BlobLimit)
            throw new InvalidOperationException();
        var text = await git.RunExact(dir, "", ct, "cat-file", "-p", sha);
        if (text == null)
            throw new InvalidOperationException();
        if (text.Contains('\0')) throw new InvalidOperationException(); return text;
    }
}
