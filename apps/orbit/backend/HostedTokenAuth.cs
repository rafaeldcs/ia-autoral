using System.Text;
using System.Text.Json.Nodes;
using System.Text.RegularExpressions;

public static partial class HostedTokens
{
    public static async Task<JsonNode?> Authenticate(Store db, string authorization)
    {
        if (string.IsNullOrEmpty(authorization) || authorization.Length > 1024) return null;
        var parts = authorization.Split(' ', 2);
        if (parts.Length != 2 || !parts[0].Equals("Basic", StringComparison.OrdinalIgnoreCase)) return null;

        try
        {
            var base64 = parts[1];
            var decoded = Convert.FromBase64String(base64);
            var auth = Encoding.UTF8.GetString(decoded);
            var split = auth.Split(':', 2);
            if (split.Length != 2) return null;

            var email = split[0];
            var token = split[1];
            if (email.Length < 1 || email.Length > 160) return null;
            if (!Regex.IsMatch(token, @"^\Aorb_[a-f0-9]{64}\z")) return null;

            var hash = Accounts.Hash(token);
            var result = await db.Query(
                "SELECT row_to_json(r)::text FROM (SELECT t.project_id,t.write_access,u.id,u.name,u.email,u.role FROM hosted_tokens t JOIN users u ON u.id=t.user_id WHERE t.hash=$1 AND lower(u.email)=lower($2) AND u.active AND NOT t.revoked AND t.expires_at>now()) r",
                hash, email
            );
            return result;
        }
        catch (FormatException) { return null; }
    }
}
