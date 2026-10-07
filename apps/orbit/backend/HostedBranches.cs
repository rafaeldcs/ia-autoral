public sealed partial class HostedRepository
{
    public async Task<string[]> Branches(Guid project, CancellationToken ct)
    {
        var output = await git.Run(DirectoryFor(project), "", ct, "for-each-ref", "--count=100", "--format=%(refname:short)", "refs/heads");
        return output.Split('\n', StringSplitOptions.RemoveEmptyEntries);
    }
}
