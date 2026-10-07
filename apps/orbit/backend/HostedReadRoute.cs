public static partial class HostedEndpoints
{
    private static async Task<IResult> Read(Guid project, HostedObjectInput input, Store db, HostedRepository repo, HttpContext c)
    {
        if (input.Sha == null || !HostedPolicy.ObjectId(input.Sha) || input.Type != "tree" && input.Type != "blob")
            return Results.BadRequest(new { error = "Objeto Git inválido." });

        if (!await Exists(project, db))
            return Results.NotFound();

        if (!await repo.Gate.WaitAsync(0, c.RequestAborted))
            return Results.Conflict(new { error = "Repositório ocupado." });

        try
        {
            return Results.Json(await repo.ReadObject(project, input.Sha, input.Type, c.RequestAborted));
        }
        catch (InvalidOperationException)
        {
            return Results.BadRequest(new { error = "Objeto indisponível, binário ou maior que 16 KB. Use git clone." });
        }
        finally
        {
            repo.Gate.Release();
        }
    }

    private static async Task<bool> Exists(Guid project, Store db)
    {
        var result = await db.Query("SELECT EXISTS(SELECT 1 FROM hosted_repositories WHERE project_id=$1)::text", project);
        return result.GetValue<bool>();
    }
}
