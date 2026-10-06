public static partial class HostedTokens
{
    private static async Task<int> CountActive(Guid project, Guid user, Store db) => (await db.Query("SELECT count(*)::text FROM hosted_tokens WHERE project_id=$1 AND user_id=$2 AND NOT revoked AND expires_at>now()", new object[] { project, user })).GetValue<int>();
}
