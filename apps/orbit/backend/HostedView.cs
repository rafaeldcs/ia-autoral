public sealed partial class HostedRepository
{
    public async Task<object> View(Guid project, Store db, CancellationToken ct)
    {
        var exists = (await db.Query("SELECT EXISTS(SELECT 1 FROM hosted_repositories WHERE project_id=$1)::text", project)).GetValue<bool>();
        if (!exists) return new { exists = false };

        var branches = await Branches(project, ct);
        string branch = branches.Contains("main") ? "main" : branches.FirstOrDefault() ?? "";
        if (string.IsNullOrEmpty(branch)) return new { head = "", commits = new object[0], entries = new object[0], exists = true, branch, branches, clonePath = "/git/" + project.ToString("D") + ".git", pushLimitMiB = 20 };

        var head = await git.Run(DirectoryFor(project), "", ct, "rev-parse", "refs/heads/" + branch);
        if (!HostedPolicy.ObjectId(head)) throw new InvalidOperationException("Invalid ObjectId(head)");

        var commits = await Commits(project, head, ct);
        var tree = await Tree(project, head, ct);
        return new { exists = true, head, branch, branches, commits, entries = tree, clonePath = "/git/" + project.ToString("D") + ".git", pushLimitMiB = 20 };
    }
}
