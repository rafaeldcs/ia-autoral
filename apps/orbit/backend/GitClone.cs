using System;
using System.IO;
using System.Threading;
using System.Threading.Tasks;

public sealed partial class GitCheckout
{


    private async Task<string> Ensure(Guid project, string url, string branch, string token, string action, CancellationToken cancel)
    {
        string root = Environment.GetEnvironmentVariable("ORBIT_REPOSITORIES") ?? "/var/lib/orbit/repos";
if (!Path.IsPathFullyQualified(root)) throw new InvalidOperationException("Pasta Git inválida.");
Directory.CreateDirectory(root);
        string path = Path.Combine(root, project.ToString("N"));

        if (!Directory.Exists(path))
        {
            if (action != "pull")
                throw new InvalidOperationException("Ação inválida para diretório não existente.");
            await process.Run(root, token, cancel, "clone", "--no-checkout", "--single-branch", "--branch", branch, "--depth", "200", "--", url, path);
            await process.Run(path, token, cancel, "checkout", branch);
        }
        else
        {
            if (!Directory.Exists(Path.Combine(path, ".git")))
                throw new InvalidOperationException("Diretório .git ausente.");
            string origin = await process.Run(path, token, cancel, "remote", "get-url", "origin");
            if (origin != url)
                throw new InvalidOperationException("URL do repositório não corresponde.");
            string currentBranch = await process.Run(path, token, cancel, "rev-parse", "--abbrev-ref", "HEAD");
            if (currentBranch != branch)
                throw new InvalidOperationException("Branch atual não corresponde.");
            string status = await process.Run(path, token, cancel, "status", "--porcelain");
            if (!string.IsNullOrEmpty(status))
                throw new InvalidOperationException("Alterações não commitadas detectadas.");
        }

        return path;
    }
}
