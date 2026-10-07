using Microsoft.AspNetCore.DataProtection;
using System.Text.Json.Nodes;
using System.Threading.Tasks;
using System.Linq;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;
using System.Threading;

public sealed partial class GitWorker(IServiceScopeFactory scopes, GitCheckout checkout, GitHubDelivery delivery, IDataProtectionProvider protection, ILogger<GitWorker> logger) : BackgroundService
{
    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        using var initial = scopes.CreateScope();
        await initial.ServiceProvider.GetRequiredService<Store>().Execute("UPDATE git_jobs SET status='failed',finished_at=now(),message='Servidor reiniciado. Confira antes de repetir.' WHERE status='running' AND phase='git'");

        await initial.ServiceProvider.GetRequiredService<Store>().Execute("UPDATE git_jobs SET status='queued' WHERE status='running' AND phase='delivery'");
while (!stoppingToken.IsCancellationRequested)
        {
            try
            {
                using var current = scopes.CreateScope();
                var db = current.ServiceProvider.GetRequiredService<Store>();
                var job = await db.Query("WITH picked AS (SELECT id FROM git_jobs WHERE status='queued' ORDER BY created_at FOR UPDATE SKIP LOCKED LIMIT 1), changed AS (UPDATE git_jobs j SET status='running' FROM picked WHERE j.id=picked.id RETURNING j.*) SELECT row_to_json(changed)::text FROM changed");
                if (job is not null) await Perform(db, job, stoppingToken);
                await Task.Delay(2000, stoppingToken);
            }
            catch (OperationCanceledException) when (stoppingToken.IsCancellationRequested) { break; }
            catch (Exception)
            {
                logger.LogWarning("Fila Git indisponível.");
                await Task.Delay(5000, stoppingToken);
            }
        }
    }
}
