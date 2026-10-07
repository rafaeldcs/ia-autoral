public sealed partial class HostedRepository
{
    public async Task<bool> ProjectExists(Guid project, Store db) =>
        (await db.Query($"SELECT EXISTS(SELECT 1 FROM projects WHERE id=$1)::text", project)).GetValue<bool>();

    public async Task<bool> RepositoryExists(Guid project, Store db) =>
        (await db.Query($"SELECT EXISTS(SELECT 1 FROM hosted_repositories WHERE project_id=$1)::text", project)).GetValue<bool>();
}
