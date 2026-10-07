using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.DataProtection;
using System.Threading.Tasks;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;
using System.Net;
public static partial class GitEndpoints
{
private static async Task<IResult> Configure(Guid project, GitInput input, Store db, HttpContext c, IDataProtectionProvider protection)
{
    if (Accounts.Role(c) != "admin")
        return Results.Json(new { error = "Somente administradores." }, statusCode: 403);

    var erro = GitPolicy.Validate(input.Url, input.Branch, input.Workflow, input.AutoDeploy);
if (erro != null || !ValidToken(input.Token))
        return Results.Json(new { error = erro ?? "Token inválido." }, statusCode: 400);

    await Gate.WaitAsync();
    try
    {
        var exists = (await db.Query("SELECT EXISTS(SELECT 1 FROM projects WHERE id=$1)::text", project)).GetValue<bool>();
        if (!exists)
            return Results.Json(new { error = "Projeto não encontrado." }, statusCode: 404);

        var running = (await db.Query("SELECT EXISTS(SELECT 1 FROM git_jobs WHERE project_id=$1 AND status IN ('queued','running'))::text", project)).GetValue<bool>();
        if (running)
            return Results.Json(new { error = "Job já em execução." }, statusCode: 409);

        var repo = await db.Query("SELECT row_to_json(r)::text FROM git_repositories r WHERE project_id=$1", project);
        if (repo != null && !string.IsNullOrEmpty(repo["head"]?.GetValue<string>()) && (input.Url != repo["url"]?.GetValue<string>() || input.Branch != repo["branch"]?.GetValue<string>()))
            return Results.Json(new { error = "Repositório já configurado." }, statusCode: 409);

        string credential = input.Token is null ? repo?["credential"]?.GetValue<string>() ?? "" : input.Token == "" ? "" : protection.CreateProtector("Orbit.Git.Credential.v1").Protect(input.Token);
        await SaveConfiguration(db, project, input, credential);
        await Accounts.Audit(db, c, "Configurou repositório " + project);
        return Results.Ok(new { ok = true });
    }
    finally
    {
        Gate.Release();
    }
}

}
