public sealed partial class HostedRepository
{
    private readonly GitProcess git;
    public HostedRepository(GitProcess git) => this.git = git;
    public SemaphoreSlim Gate { get; } = new(1, 1);
    public string Root => Path.Combine(Environment.GetEnvironmentVariable("ORBIT_REPOSITORIES") ?? "/tmp/orbit-repos", "hosted");

    public string DirectoryFor(Guid guid) => Path.Combine(Root, guid.ToString() + ".git");

    public async Task Create(Guid project, Store db, CancellationToken ct)
    {
        if (await ProjectExists(project, db) is false) throw new KeyNotFoundException();
        if (await RepositoryExists(project, db)) throw new InvalidOperationException();
        Directory.CreateDirectory(Root);
        var dir = DirectoryFor(project);
        Directory.CreateDirectory(dir);
        if (!File.Exists(Path.Combine(dir, "HEAD")))
            await git.Run(dir, "", ct, "init", "--bare", "--initial-branch=main");
        var config = new[]
        {
            ("core.hooksPath", "/dev/null"),
            ("http.getanyfile", "false"),
            ("receive.denyNonFastForwards", "true"),
            ("receive.denyDeletes", "true"),
            ("receive.fsckObjects", "true"),
            ("transfer.fsckObjects", "true"),
            ("receive.maxInputSize", "20971520"),
            ("gc.auto", "0")
        };
        foreach (var (k, v) in config) await git.Run(dir, "", ct, "config", k, v);
        await db.Execute("INSERT INTO hosted_repositories(project_id) VALUES($1) ON CONFLICT DO NOTHING", project);
    }
}
