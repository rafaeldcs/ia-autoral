using System.Text.RegularExpressions;

public static partial class GitPolicy
{
    public static string? Validate(string url, string branch, string workflow, bool autoDeploy)
    {
        if (!ValidUrl(url)) return "URL do GitHub inválida.";
        if (!ValidBranch(branch)) return "Branch inválida.";
        if (workflow != "orbit-hml.yml") return "Pipeline inválido.";
        if (autoDeploy && (url != "https://github.com/rafaeldcs/ia-autoral.git" || branch != "codex/local-learning-execution"))
            return "Deploy permitido somente para o Orbit na homologação.";
        return null;
    }

    public static bool CanManage(string role) => role is "admin" or "manager";

    public static bool ValidSha(string sha) => sha != null && Regex.IsMatch(sha, @"\A[a-f0-9]{40}\z");
}
