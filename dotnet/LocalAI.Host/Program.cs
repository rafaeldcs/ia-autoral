using System.Net;
using System.Net.Http.Headers;

// Optional .NET facade. The tested reference backend still runs locally in Python.
// No external service, pretrained model, or arbitrary upstream URL is configured here.
var backendPort = 8765;
var setting = Environment.GetEnvironmentVariable("LOCALAI_BACKEND_PORT");
if (setting is not null && (!int.TryParse(setting, out backendPort) || backendPort is < 1024 or > 65535))
    throw new InvalidOperationException("LOCALAI_BACKEND_PORT must be a local port between 1024 and 65535.");

var webroot = Path.Combine(AppContext.BaseDirectory, "wwwroot");
var builder = WebApplication.CreateBuilder(new WebApplicationOptions { Args = args, WebRootPath = webroot });
builder.WebHost.ConfigureKestrel(options =>
{
    options.Listen(IPAddress.Loopback, 5080);
    options.Limits.MaxRequestBodySize = 2_500_000;
    options.Limits.RequestHeadersTimeout = TimeSpan.FromSeconds(15);
});
builder.Services.AddHttpClient("local-core", client =>
{
    client.BaseAddress = new Uri($"http://127.0.0.1:{backendPort}/");
    client.Timeout = TimeSpan.FromSeconds(120);
}).ConfigurePrimaryHttpMessageHandler(() => new SocketsHttpHandler
{
    AllowAutoRedirect = false,
    UseCookies = false,
    UseProxy = false
});
var app = builder.Build();
app.Use(async (context, next) =>
{
    var host = context.Request.Host;
    var allowedHost = (host.Host == "127.0.0.1" || host.Host == "localhost") && host.Port == 5080;
    var origin = context.Request.Headers.Origin.ToString();
    var allowedOrigin = string.IsNullOrEmpty(origin) || origin is "http://127.0.0.1:5080" or "http://localhost:5080";
    var fetchSite = context.Request.Headers["Sec-Fetch-Site"].ToString();
    if (!allowedHost || !allowedOrigin || fetchSite is "cross-site" or "same-site")
    {
        context.Response.StatusCode = StatusCodes.Status403Forbidden;
        await context.Response.WriteAsJsonAsync(new { error = "Origem não autorizada." });
        return;
    }
    context.Response.Headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; object-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'";
    context.Response.Headers["X-Content-Type-Options"] = "nosniff";
    context.Response.Headers["Referrer-Policy"] = "no-referrer";
    context.Response.Headers.CacheControl = "no-store";
    await next();
});
app.UseDefaultFiles();
app.UseStaticFiles();
app.MapMethods("/api/{**path}", ["GET", "POST"], async (HttpContext context, IHttpClientFactory factory) =>
{
    var authorization = context.Request.Headers.Authorization.ToString();
    if (!AuthenticationHeaderValue.TryParse(authorization, out var auth) || auth.Scheme != "Bearer")
    {
        context.Response.StatusCode = StatusCodes.Status401Unauthorized;
        await context.Response.WriteAsJsonAsync(new { error = "Token local obrigatório." });
        return;
    }
    using var request = new HttpRequestMessage(new HttpMethod(context.Request.Method), context.Request.Path.ToString() + context.Request.QueryString.ToString());
    request.Headers.Authorization = auth;
    if (HttpMethods.IsPost(context.Request.Method))
    {
        if (!context.Request.HasJsonContentType())
        {
            context.Response.StatusCode = StatusCodes.Status415UnsupportedMediaType;
            return;
        }
        // Buffered to supply a Content-Length; the core intentionally rejects chunked bodies.
        using var buffer = new MemoryStream();
        await context.Request.Body.CopyToAsync(buffer, context.RequestAborted);
        if (buffer.Length > 2_500_000)
        {
            context.Response.StatusCode = StatusCodes.Status413PayloadTooLarge;
            return;
        }
        request.Content = new ByteArrayContent(buffer.ToArray());
        request.Content.Headers.ContentType = new MediaTypeHeaderValue("application/json");
    }
    try
    {
        using var response = await factory.CreateClient("local-core").SendAsync(request, HttpCompletionOption.ResponseHeadersRead, context.RequestAborted);
        context.Response.StatusCode = (int)response.StatusCode;
        context.Response.ContentType = response.Content.Headers.ContentType?.ToString() ?? "application/json";
        await response.Content.CopyToAsync(context.Response.Body, context.RequestAborted);
    }
    catch (HttpRequestException)
    {
        context.Response.StatusCode = StatusCodes.Status503ServiceUnavailable;
        await context.Response.WriteAsJsonAsync(new { error = "Núcleo local indisponível. Inicie scripts/start.ps1; não há fallback remoto." });
    }
});
app.Run();
