using Microsoft.AspNetCore.Http;

public static partial class HostedCgi {
    private static void ApplyHeaders(string header, HttpResponse response) {
        var lines = header.Split('\n');
        foreach (var line in lines) {
            var trimmed = line.Trim();
            if (string.IsNullOrEmpty(trimmed)) continue;
            var parts = trimmed.Split(':', 2);
            if (parts.Length < 2) continue;
            var key = parts[0].Trim().ToLower();
            var val = parts[1].Trim();
            if (key == "status") {
                if (int.TryParse(val.Trim().Split(' ', 2)[0], out int code) && new[] {200,400,403,404,500}.Contains(code))
                    response.StatusCode = code;
                else response.StatusCode = 500;
            } else if (key == "content-type" || key == "expires") {
                response.Headers[key] = val;
            }
        }
        response.Headers["Cache-Control"] = "no-store";
        response.Headers["X-Content-Type-Options"] = "nosniff";
    }
}
