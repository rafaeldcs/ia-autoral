using System.Text.RegularExpressions;

public static partial class GitPolicy {
    public static bool ValidUrl(string url) {
        if (url == null) return false;
        var match = Regex.Match(url, @"\Ahttps://github\.com/[A-Za-z0-9-]{1,39}/(?<repo>[A-Za-z0-9_.-]{1,100})\.git\z");
        if (!match.Success) return false;
        string repo = match.Groups["repo"].Value;
        return !repo.Equals(".") && !repo.Equals("..") && !repo.EndsWith(".git");
    }
}
