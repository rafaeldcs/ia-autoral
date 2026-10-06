public static partial class HostedEndpoints
{
    private static async Task<IResult> Create(Guid project, Store db, HostedRepository repo, HttpContext c)
    {
        if (!HostedPolicy.CanCreate(Accounts.Role(c)))
            return Results.Json(new { error = "Somente administradores ou gestores criam repositórios." }, statusCode: 403);

        if (!await repo.Gate.WaitAsync(0, c.RequestAborted))
            return Results.Conflict(new { error = "Repositório ocupado." });

        try
        {
            await repo.Create(project, db, c.RequestAborted);
            await Accounts.Audit(db, c, "Criou repositório hospedado " + project);
            return Results.Created("", new { ok = true });
        }
        catch (InvalidOperationException)
        {
            return Results.Conflict(new { error = "O repositório já existe ou está indisponível." });
        }
        finally
        {
            repo.Gate.Release();
        }
    }
}
