using System.Text.Json;
public sealed partial class GitCheckout
{
public async Task<(string Head, string Commits)> Execute(Guid project, string url, string branch, string token, string action, string expected, CancellationToken cancel)
{
    if (action != "pull" && action != "push" && action != "deploy")
        throw new ArgumentException("Action must be pull, push, or deploy.");

    string path = await Ensure(project, url, branch, token, action, cancel);
    string head = await process.Run(path, token, cancel, "rev-parse", "HEAD");

    if (action == "push" || action == "deploy")
    {
        if (!GitPolicy.ValidSha(expected) || expected != head)
            throw new InvalidOperationException("Expected SHA does not match current HEAD.");
    }

    if (action == "pull")
    {
        await process.Run(path, token, cancel, "fetch", "--depth", "200", "origin", branch);
        await process.Run(path, token, cancel, "merge", "--ff-only", "FETCH_HEAD");
    }
    else if (action == "push")
    {
        await process.Run(path, token, cancel, "push", "origin", "HEAD:refs/heads/" + branch);
    }

    head = await process.Run(path, token, cancel, "rev-parse", "HEAD");

    return (head, await Commits(path, token, cancel));
}

}
