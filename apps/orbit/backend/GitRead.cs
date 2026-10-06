public static partial class GitEndpoints {
    public static void MapRead(WebApplication app) {
        app.MapGet("/api/projects/{project:guid}/git", async (Guid project, Store db) => {
            var repository = await db.Query(
                "SELECT row_to_json(r)::text FROM (SELECT url,branch,workflow,auto_deploy AS \"autoDeploy\",head,commits,credential<>'' AS \"hasCredential\" FROM git_repositories WHERE project_id=$1) r",
                project
            );
            var jobs = await db.Query(
                "SELECT coalesce(json_agg(r ORDER BY r.\"createdAt\" DESC),'[]')::text FROM (SELECT id,action,status,head,message,created_at AS \"createdAt\",finished_at AS \"finishedAt\" FROM git_jobs WHERE project_id=$1 ORDER BY created_at DESC LIMIT 30) r",
                project
            );
            return Results.Json(new { repository, jobs });
        });
    }
}
