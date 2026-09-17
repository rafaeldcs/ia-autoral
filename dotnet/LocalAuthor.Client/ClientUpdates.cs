using System.Diagnostics;
using System.Net;
using System.Security.Cryptography;
using System.Text.Json;
using LocalAuthor.Connectivity;

namespace LocalAuthor.Client;

static class ClientUpdates {
 public static readonly string UpdateRoot = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "LocalAuthorClient", "updates");
 public static Version CurrentVersion => typeof(ClientUpdates).Assembly.GetName().Version!;
 internal static HttpClient CreateClient(Connection connection) {
  connection.Validate();
  var handler = new HttpClientHandler { UseProxy = false, AllowAutoRedirect = false,
   ServerCertificateCustomValidationCallback = (_, cert, _, _) => cert != null && connection.Matches(cert) };
  var client = new HttpClient(handler) { BaseAddress = new Uri(connection.Server), Timeout = TimeSpan.FromMinutes(5) };
  client.DefaultRequestHeaders.Authorization = new("Bearer", connection.AccessKey);
  return client;
 }
 public static async Task<ClientRelease?> CheckAsync(Connection connection, CancellationToken cancel) {
  using var timeout = CancellationTokenSource.CreateLinkedTokenSource(cancel); timeout.CancelAfter(TimeSpan.FromSeconds(5));
  using var client = CreateClient(connection);
  using var response = await client.GetAsync("/api/client-update", HttpCompletionOption.ResponseHeadersRead, timeout.Token);
  if (response.StatusCode == HttpStatusCode.NotFound) return null;
  response.EnsureSuccessStatusCode();
  using var stream = await response.Content.ReadAsStreamAsync(timeout.Token);
  var bytes = new byte[4097]; int used = 0, count;
  while (used < bytes.Length && (count = await stream.ReadAsync(bytes.AsMemory(used), timeout.Token)) > 0) used += count;
  if (used > 4096) throw new InvalidDataException("Manifesto muito grande.");
  var release = JsonSerializer.Deserialize<ClientRelease>(bytes.AsSpan(0, used), ClientRelease.Json) ?? throw new InvalidDataException();
  return release.Validate() > CurrentVersion && !File.Exists(Path.Combine(UpdateRoot, "blocked-" + release.Sha256)) ? release : null;
 }
 public static async Task<string> DownloadAsync(Connection connection, ClientRelease release, CancellationToken cancel) {
  if (release.Validate() <= CurrentVersion) throw new InvalidDataException("Versão antiga recusada.");
  Directory.CreateDirectory(UpdateRoot); UpdateInstaller.RejectLinks(UpdateRoot);
  var folder = Path.Combine(UpdateRoot, Guid.NewGuid().ToString("N")); Directory.CreateDirectory(folder);
  var target = Path.Combine(folder, "download.exe");
  try {
   using var client = CreateClient(connection);
   using var deadline = CancellationTokenSource.CreateLinkedTokenSource(cancel); deadline.CancelAfter(TimeSpan.FromMinutes(5));
   using var response = await client.GetAsync("/api/client-update/package?sha256=" + release.Sha256, HttpCompletionOption.ResponseHeadersRead, deadline.Token);
   response.EnsureSuccessStatusCode();
   if (response.Content.Headers.ContentLength != release.Size) throw new InvalidDataException("Tamanho da publicação divergente.");
   using (var input = await response.Content.ReadAsStreamAsync(deadline.Token))
   using (var output = new FileStream(target, FileMode.CreateNew, FileAccess.Write, FileShare.None, 81920, true)) {
    var buffer = new byte[81920]; long total = 0; int count;
    while ((count = await input.ReadAsync(buffer, deadline.Token)) > 0) {
     total += count; if (total > release.Size) throw new InvalidDataException("Download maior que a publicação.");
     await output.WriteAsync(buffer.AsMemory(0, count), deadline.Token);
    }
   }
   await release.VerifyAsync(target, deadline.Token);
   var version = Version.Parse(FileVersionInfo.GetVersionInfo(target).FileVersion!);
   if (version != release.Validate()) throw new InvalidDataException("Versão do executável divergente.");
   return folder;
  } catch { if (File.Exists(target)) File.Delete(target); throw; }
 }
 public static async Task LaunchAsync(string folder, ClientRelease release, CancellationToken cancel) {
  var job = new UpdateJob(Environment.ProcessPath!, Environment.ProcessId, Process.GetCurrentProcess().StartTime.ToUniversalTime().Ticks, release);
  var path = Path.Combine(folder, "job.bin");
  File.WriteAllBytes(path, ProtectedData.Protect(JsonSerializer.SerializeToUtf8Bytes(job), null, DataProtectionScope.CurrentUser));
  var helper = Path.Combine(folder, "updater.exe"); File.Copy(Environment.ProcessPath!, helper, false);
  var info = new ProcessStartInfo(helper) { UseShellExecute = false, CreateNoWindow = true, WindowStyle = ProcessWindowStyle.Hidden };
  info.ArgumentList.Add("--apply-update"); info.ArgumentList.Add(path);
  using var process = Process.Start(info) ?? throw new IOException("Não foi possível iniciar o atualizador.");
  for (int i = 0; i < 100; i++) {
   if (File.Exists(Path.Combine(folder, "ready"))) return;
   if (process.HasExited) throw new IOException("O atualizador não conseguiu preparar a instalação.");
   await Task.Delay(100, cancel);
  }
  throw new IOException("O atualizador não respondeu; o aplicativo continuará aberto.");
 }
}
