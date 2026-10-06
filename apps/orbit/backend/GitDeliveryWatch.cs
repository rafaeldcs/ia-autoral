using System.Text.Json;
using System.Text.RegularExpressions;
using System.Net.Http;
using System.Threading;
using System.Threading.Tasks;
using System.Collections.Generic;
using System.Linq;

public sealed partial class GitHubDelivery
{
    private static async Task<string> Watch(HttpClient client, string branch, string sha, CancellationToken ct, bool allowRerun)
    {
        bool rerun = false;
        bool seenRunning = false;
        int previousAttempt = 0;
        long selectedId = 0;
        while (true)
        {
            using HttpResponseMessage response = await client.GetAsync("https://api.github.com/repos/rafaeldcs/ia-autoral/actions/workflows/orbit-hml.yml/runs?per_page=20", ct);
            if (!response.IsSuccessStatusCode)
                throw new System.Exception("Erro ao obter runs do GitHub");
            using JsonDocument doc = JsonDocument.Parse(await response.Content.ReadAsStringAsync(ct));
            var candidates = doc.RootElement.GetProperty("workflow_runs").EnumerateArray()
                .Where(r => r.GetProperty("head_sha").GetString() == sha && r.GetProperty("head_branch").GetString() == branch)
                .OrderByDescending(r => r.GetProperty("id").GetInt64())
                .ToArray();
            if (candidates.Length == 0)
            {
                await Task.Delay(5000, ct);
                continue;
            }
            var run = candidates[0];
            if (selectedId == 0)
                selectedId = run.GetProperty("id").GetInt64();
            run = candidates.First(r => r.GetProperty("id").GetInt64() == selectedId);
if (run.GetProperty("status").GetString() != "completed")
            {
                seenRunning = true;
                await Task.Delay(5000, ct);
                continue;
            }
            if (!rerun && !seenRunning && allowRerun)
            {
                using HttpResponseMessage rerunResponse = await client.PostAsync($"https://api.github.com/repos/rafaeldcs/ia-autoral/actions/runs/{selectedId}/rerun", null, ct);
                if (rerunResponse.StatusCode != System.Net.HttpStatusCode.Created)
                    throw new System.Exception("Falha ao reexecutar");
                previousAttempt = run.GetProperty("run_attempt").GetInt32();
                rerun = true;
                await Task.Delay(5000, ct);
                continue;
            }
            if (run.GetProperty("run_attempt").GetInt32() > previousAttempt)
            {
                var conclusion = run.GetProperty("conclusion").GetString();
                if (conclusion != "success")
                    throw new System.Exception("Execução não foi bem-sucedida");
                string htmlUrl = run.GetProperty("html_url").GetString() ?? "";
                if (!Regex.IsMatch(htmlUrl, @"\Ahttps://github\.com/rafaeldcs/ia-autoral/actions/runs/[0-9]+\z"))
                    throw new System.Exception("URL inválida");
                return htmlUrl;
            }
            await Task.Delay(5000, ct);
        }
    }
}
