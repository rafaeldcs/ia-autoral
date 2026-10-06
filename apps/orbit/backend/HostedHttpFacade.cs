public static partial class HostedHttp {
    public static async Task Handle(HttpContext c) {
        try { await Execute(c); }
        catch (OperationCanceledException) { c.Abort(); }
        catch (InvalidOperationException) {
            if (c.Response.HasStarted) c.Abort(); else c.Response.StatusCode = 400;
        }
        catch { if (c.Response.HasStarted) c.Abort(); else c.Response.StatusCode = 503; }
    }
}
