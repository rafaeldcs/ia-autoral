using System.Threading.Tasks;

public static partial class GitEndpoints
{
    private static async Task<int> SaveConfiguration(Store db, Guid project, GitInput input, string credential)
    {
        string SQL = @"INSERT INTO git_repositories(project_id,url,branch,workflow,auto_deploy,credential) VALUES($1,$2,$3,$4,$5,$6) ON CONFLICT(project_id) DO UPDATE SET url=EXCLUDED.url,branch=EXCLUDED.branch,workflow=EXCLUDED.workflow,auto_deploy=EXCLUDED.auto_deploy,credential=EXCLUDED.credential,updated_at=now()";
        return await db.Execute(SQL, project, input.Url, input.Branch, input.Workflow, input.AutoDeploy, credential);
    }
}
