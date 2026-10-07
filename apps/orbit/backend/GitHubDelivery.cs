using System.Net.Http.Headers;
using System.Threading;
using System.Threading.Tasks;
using System.Net.Http;
using System;

public sealed partial class GitHubDelivery
{
    public async Task<string> Run(string url, string branch, string sha, string token, CancellationToken stop, bool allowRerun=true)
    {
        if (string.IsNullOrEmpty(token))
            throw new InvalidOperationException("Token não pode ser vazio.");
        if (GitPolicy.Validate(url, branch, "orbit-hml.yml", true) != null)
            throw new InvalidOperationException("Validação de política falhou.");
        if (!GitPolicy.ValidSha(sha))
            throw new InvalidOperationException("SHA inválida.");

        using var client = new HttpClient(new HttpClientHandler { AllowAutoRedirect = false }) { Timeout = TimeSpan.FromSeconds(30), MaxResponseContentBufferSize = 1048576 };
        client.DefaultRequestHeaders.UserAgent.ParseAdd("Orbit-HML/1.0");
        client.DefaultRequestHeaders.Accept.ParseAdd("application/vnd.github+json");
        client.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", token);
        client.DefaultRequestHeaders.Add("X-GitHub-Api-Version", "2022-11-28");

        using var deadline = CancellationTokenSource.CreateLinkedTokenSource(stop);
        deadline.CancelAfter(TimeSpan.FromMinutes(15));

        try
        {
            return await Watch(client, branch, sha, deadline.Token, allowRerun);
        }
        catch (OperationCanceledException) when (!stop.IsCancellationRequested)
        {
            throw new InvalidOperationException("A entrega excedeu o tempo limite. Confira o pipeline antes de repetir.");
        }
    }
}
