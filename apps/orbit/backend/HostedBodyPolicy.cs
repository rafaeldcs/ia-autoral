public static partial class HostedHttp {
    private static bool RequireBody(HttpContext c, HostedRoute route) {
        if (c.Request.Method == "GET" && c.Request.ContentLength > 0) {
            c.Response.StatusCode = 400; return false;
        }
        if (c.Request.Method == "POST") {
            if (c.Request.ContentType != $"application/x-git-{route.Service}-request" || c.Request.Headers.ContainsKey("Content-Encoding")) {
                c.Response.StatusCode = 400; return false;
            }
            if (c.Request.ContentLength > HostedPolicy.InputLimit) {
                c.Response.StatusCode = 413; return false;
            }
        }
        return true;
    }
}
