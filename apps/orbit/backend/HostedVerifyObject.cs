public sealed partial class HostedRepository
{
    public async Task VerifyObject(Guid project, string sha, string type, CancellationToken ct)
    {
        if (!HostedPolicy.ObjectId(sha) || type != "tree" && type != "blob")
            throw new InvalidOperationException();
        var dir = DirectoryFor(project);
        var output = await git.Run(dir, "", ct, "rev-list", "--objects", "--all", "--no-object-names");
        if (!output.Split('\n').Contains(sha))
            throw new InvalidOperationException();
        var actualType = await git.Run(dir, "", ct, "cat-file", "-t", sha);
        if (actualType != type)
            throw new InvalidOperationException();
    }
}
