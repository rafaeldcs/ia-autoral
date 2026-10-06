public static partial class HostedTokens
{
    public static async Task<IResult> Revoke(Guid project, Guid id, Store db, HttpContext c)
    {
        var currentuserid = Guid.Parse(Accounts.User(c)["id"]!.GetValue<string>());
        var rows = await db.Execute("UPDATE hosted_tokens SET revoked=true WHERE id=$1 AND project_id=$2 AND user_id=$3", id, project, currentuserid);
        if (rows == 0) return Results.NotFound(new { error = "Token não encontrado." });
        await Accounts.Audit(db, c, "Revogou token Git " + id);
        return Results.Ok(new { ok = true });
    }
}
