using Microsoft.AspNetCore.DataProtection;
using System.Text.Json.Nodes;
using System.Threading;
using System.Threading.Tasks;

public sealed partial class GitWorker
{




    private async Task<string> ExecuteJob(Store db, JsonNode job, Guid project, Guid actor, CancellationToken stop)
    {
        var user = await db.Query("SELECT row_to_json(u)::text FROM (SELECT role,name FROM users WHERE id=$1 AND active) u", new object[] { actor });
        if (user == null || !GitPolicy.CanManage(user["role"]!.GetValue<string>()))
            throw new InvalidOperationException("Acesso negado");

        var repo = await db.Query("SELECT row_to_json(r)::text FROM git_repositories r WHERE project_id=$1", new object[] { project });
        if (repo == null)
            throw new InvalidOperationException("Repositório não encontrado");

        var url = repo["url"]!.GetValue<string>();
        var branch = repo["branch"]!.GetValue<string>();
        var credential = repo["credential"]!.GetValue<string>();
        var autoDeploy = repo["auto_deploy"]!.GetValue<bool>();

        if (string.IsNullOrEmpty(credential))
            credential = "";
        else
            credential = protection.CreateProtector("Orbit.Git.Credential.v1").Unprotect(credential);

        if (GitPolicy.Validate(url, branch, "orbit-hml.yml", autoDeploy) != null)
            throw new InvalidOperationException("Validação falhou");

        var action = job["action"]!.GetValue<string>();
        var expected = job["expected_head"]!.GetValue<string>();

if (job["phase"]?.GetValue<string>() == "delivery") return await delivery.Run(url, branch, job["head"]!.GetValue<string>(), credential, stop, false);

        var result = await checkout.Execute(project, url, branch, credential, action, expected, stop);
        await db.Execute("UPDATE git_repositories SET head=$2,commits=$3::jsonb,updated_at=now() WHERE project_id=$1", new object[] { project, result.Head, result.Commits });
        await db.Execute("UPDATE git_jobs SET head=$2 WHERE id=$1", new object[] { Guid.Parse(job["id"]!.GetValue<string>()), result.Head });
        await db.Execute("INSERT INTO audit(actor,action) VALUES($1,$2)", new object[] { user["name"]!.GetValue<string>(), "Git " + action + " " + project });

if (action == "deploy" || (action == "push" && autoDeploy))
{
    await db.Execute("UPDATE git_jobs SET phase='delivery' WHERE id=$1", Guid.Parse(job["id"]!.GetValue<string>()));
    return await delivery.Run(url, branch, result.Head, credential, stop);
}


        return "Operação concluída.";
    }
}
