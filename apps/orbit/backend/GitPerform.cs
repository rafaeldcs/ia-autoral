using System.Text.Json.Nodes;
using System.Threading.Tasks;
using System;

public sealed partial class GitWorker
{
    private async Task Perform(Store db, JsonNode job, CancellationToken stop)
    {
        Guid id = Guid.Parse(job["id"]!.GetValue<string>());
        Guid project = Guid.Parse(job["project_id"]!.GetValue<string>());
        Guid actor = Guid.Parse(job["actor_id"]!.GetValue<string>());
        try
        {
            var message = await ExecuteJob(db, job, project, actor, stop);
            await db.Execute("UPDATE git_jobs SET status='succeeded',message=$2,finished_at=now() WHERE id=$1", id, message);
        }
catch (OperationCanceledException) when (stop.IsCancellationRequested) {
    var phase = (await db.Query("SELECT to_json(phase)::text FROM git_jobs WHERE id=$1", id))?.GetValue<string>();
    if (phase != "delivery") await db.Execute("UPDATE git_jobs SET status='failed',message=$2,finished_at=now() WHERE id=$1", id, "Servidor interrompido. Confira antes de repetir.");
}

        catch (Exception)
        {
            await db.Execute("UPDATE git_jobs SET status='failed',message=$2,finished_at=now() WHERE id=$1", id, "Operação falhou. Confira permissões, conexão e revisão.");
            logger.LogWarning("Operação Git falhou para {Job}", id);
        }
    }
}
