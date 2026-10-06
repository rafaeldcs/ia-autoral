using System.Text.RegularExpressions;

public static class HostedWebPolicy
{
    public static bool ReadOnlyPost(string path, string method)
    {
        if (method != "POST") return false;
        return Regex.IsMatch(path, @"\A/api/projects/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/repository/(object|tokens|tokens/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/revoke)\z", RegexOptions.IgnoreCase);
    }
}
