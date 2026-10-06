public static partial class HostedEndpoints
{
    private static async Task<IResult> List(Guid project, Store db, HttpContext c)
    {
        var user = Guid.Parse(Accounts.User(c)["id"]!.GetValue<string>());
        string sql = @"SELECT coalesce(json_agg(r ORDER BY r.""createdAt"" DESC),'[]')::text FROM (SELECT id,label,write_access AS ""write"",expires_at AS ""expiresAt"",revoked,created_at AS ""createdAt"" FROM hosted_tokens WHERE project_id=$1 AND user_id=$2) r";
        var result = await db.Query(sql, project, user);
        return Results.Json(result);
    }
}
