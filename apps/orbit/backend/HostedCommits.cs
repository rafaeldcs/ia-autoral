public sealed partial class HostedRepository
{
    public async Task<object[]> Commits(Guid project, string head, CancellationToken ct)
    {
        if (!HostedPolicy.ObjectId(head)) throw new InvalidOperationException();
        var output = await git.Run(DirectoryFor(project), "", ct, "log", "-20", "--format=%H%x09%s", head);
        return output.Split('\n')
            .Where(s => !string.IsNullOrEmpty(s))
            .Select(line => {
                var parts = line.Split('\t', 2);
                return new { sha = parts[0], subject = parts.Length >= 2 ? parts[1].Substring(0, Math.Min(500, parts[1].Length)) : string.Empty };
            }).ToArray();
    }
}
