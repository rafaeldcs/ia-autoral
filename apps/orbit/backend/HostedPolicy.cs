public static class HostedPolicy
{
    public const int InputLimit = 20 * 1024 * 1024;
    public const int OutputLimit = 32 * 1024 * 1024;
    public const int BlobLimit = 16000;

    public static bool CanWrite(string role)
    {
        return role == "admin" || role == "manager" || role == "member";
    }

    public static bool CanCreate(string role)
    {
        return role == "admin" || role == "manager";
    }

    public static bool ObjectId(string value)
    {
        if (string.IsNullOrEmpty(value) || value.Length != 40)
        {
            return false;
        }

        return System.Text.RegularExpressions.Regex.IsMatch(value, @"^\A[a-f0-9]{40}\z");
    }

    public static string? Service(string method, string endpoint, string query)
    {
        if (string.IsNullOrEmpty(method) || string.IsNullOrEmpty(endpoint))
        {
            return null;
        }

        if (method == "GET" && endpoint == "info/refs" && query == "service=git-upload-pack")
        {
            return "upload-pack";
        }

        if (method == "GET" && endpoint == "info/refs" && query == "service=git-receive-pack")
        {
            return "receive-pack";
        }

        if (method == "POST" && endpoint == "git-upload-pack" && query == "")
        {
            return "upload-pack";
        }

        if (method == "POST" && endpoint == "git-receive-pack" && query == "")
        {
            return "receive-pack";
        }

        return null;
    }
}
