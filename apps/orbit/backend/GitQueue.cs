using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Routing;
using Microsoft.AspNetCore.Http;
using System.Threading.Tasks;
using System;
using System.Linq;
using JsonNode = System.Text.Json.Nodes.JsonObject;

public record GitActionInput(string Action, string? ExpectedHead);

public static partial class GitEndpoints
{
    public static void MapQueue(WebApplication app)
    {
        app.MapPost("/api/projects/{project:guid}/git/jobs", async (Guid project, GitActionInput input, Store db, HttpContext c) =>
        {
            if (!Accounts.Manage(c))
                return Results.Json(new { error = "Permissão insuficiente." }, statusCode: 403);

            if (string.IsNullOrEmpty(input.Action) || !new[] { "pull", "push", "deploy" }.Contains(input.Action.ToLower()))
                return Results.BadRequest(new { error = "Ação inválida." });

            if (input.Action.ToLower() == "push" || input.Action.ToLower() == "deploy")
            {
                if (!GitPolicy.ValidSha(input.ExpectedHead ?? ""))
                    return Results.BadRequest(new { error = "SHA inválido." });
            }

            var gate = new object();
            await Gate.WaitAsync();
            try
            {
                var repo = await db.Query("SELECT row_to_json(r)::text FROM (SELECT auto_deploy FROM git_repositories WHERE project_id=$1) r", project);
                if (repo == null)
                    return Results.NotFound();

                if (input.Action.ToLower() == "deploy" && !repo["auto_deploy"]!.GetValue<bool>())
                    return Results.BadRequest(new { error = "Autodeploy não habilitado." });

                var id = Guid.NewGuid();
                var actor = Guid.Parse(Accounts.User(c)["id"]!.GetValue<string>());

                var result = await db.Execute("INSERT INTO git_jobs(id,project_id,actor_id,action,status,expected_head) VALUES($1,$2,$3,$4,'queued',$5)", id, project, actor, input.Action, input.ExpectedHead ?? "");

                if (result <= 0)
                    return Results.StatusCode(409);

                await Accounts.Audit(db, c, $"Job {id} criado para {input.Action} em {project}");

                return Results.Accepted(null, new { id, status = "queued" });
            }
            finally
            {
                Gate.Release();
            }
        });
    }
}
