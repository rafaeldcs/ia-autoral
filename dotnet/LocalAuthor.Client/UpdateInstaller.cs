using System.Diagnostics;
using System.Security.Cryptography;
using System.Text.Json;
using LocalAuthor.Connectivity;

namespace LocalAuthor.Client;

record UpdateJob(string Target, int ParentId, long ParentStarted, ClientRelease Release);

static class UpdateInstaller {
 public static void RejectLinks(string path) {
  for (var current = new DirectoryInfo(Path.GetFullPath(path)); current != null; current = current.Parent)
   if ((current.Attributes & FileAttributes.ReparsePoint) != 0) throw new IOException("Pasta de atualização não pode ser um link.");
 }
 static string ValidateJobPath(string path) {
  path = Path.GetFullPath(path); var folder = Path.GetDirectoryName(path)!;
  if (Path.GetFileName(path) != "job.bin" || !string.Equals(Path.GetDirectoryName(folder), ClientUpdates.UpdateRoot, StringComparison.OrdinalIgnoreCase) ||
      !Guid.TryParseExact(Path.GetFileName(folder), "N", out _)) throw new InvalidDataException("Caminho da atualização inválido.");
  RejectLinks(folder); return folder;
 }
 public static void Acknowledge(string path) {
  var folder = ValidateJobPath(path);
  var job = ReadJob(path);
  if (!string.Equals(job.Target, Environment.ProcessPath, StringComparison.OrdinalIgnoreCase) || ClientUpdates.CurrentVersion != job.Release.Validate())
   throw new InvalidDataException("Confirmação de versão divergente.");
  File.WriteAllText(Path.Combine(folder, "started"), "ok");
 }
 static UpdateJob ReadJob(string path) {
  if (new FileInfo(path).Length > 65536 || (File.GetAttributes(path) & FileAttributes.ReparsePoint) != 0) throw new InvalidDataException();
  return JsonSerializer.Deserialize<UpdateJob>(ProtectedData.Unprotect(File.ReadAllBytes(path), null, DataProtectionScope.CurrentUser)) ?? throw new InvalidDataException();
 }
 public static async Task<int> ApplyAsync(string path) {
  string? folder = null, backup = null, target = null; bool replaced = false;
  try {
   folder = ValidateJobPath(path); var job = ReadJob(path); target = Path.GetFullPath(job.Target);
   if (Path.GetFileName(target) != "LocalAuthor.Client.exe" || (File.GetAttributes(target) & FileAttributes.ReparsePoint) != 0)
    throw new InvalidDataException("Destino da atualização inválido.");
   RejectLinks(Path.GetDirectoryName(target)!);
   using var updateLock = new FileStream(target + ".update-lock", FileMode.OpenOrCreate, FileAccess.ReadWrite, FileShare.None);
   using var parent = Process.GetProcessById(job.ParentId);
   if (parent.StartTime.ToUniversalTime().Ticks != job.ParentStarted || !string.Equals(parent.MainModule?.FileName, target, StringComparison.OrdinalIgnoreCase))
    throw new InvalidDataException("O processo de origem não corresponde ao aplicativo.");
   if (job.Release.Validate() <= Version.Parse(FileVersionInfo.GetVersionInfo(target).FileVersion!)) throw new InvalidDataException("Versão antiga recusada.");
   var source = Path.Combine(folder, "download.exe");
   if ((File.GetAttributes(source) & FileAttributes.ReparsePoint) != 0) throw new InvalidDataException();
   await job.Release.VerifyAsync(source);
   if (Version.Parse(FileVersionInfo.GetVersionInfo(source).FileVersion!) != job.Release.Validate()) throw new InvalidDataException("Versão divergente.");
   File.WriteAllText(Path.Combine(folder, "ready"), "ok");
   using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(45));
   await parent.WaitForExitAsync(timeout.Token);
   // Stage on the same volume as the destination; the previous executable remains recoverable.
   var pending = target + "." + Path.GetFileName(folder) + ".pending";
   backup = target + "." + Path.GetFileName(folder) + ".previous";
   File.Copy(source, pending, false); await job.Release.VerifyAsync(pending);
   File.Replace(pending, target, backup); replaced = true;
   File.WriteAllText(Path.Combine(folder, "state.json"), "{\"state\":\"replaced\"}");
   var info = new ProcessStartInfo(target) { UseShellExecute = false, WorkingDirectory = Path.GetDirectoryName(target)! };
   info.ArgumentList.Add("--updated"); info.ArgumentList.Add(path);
   var testMarker = Path.Combine(folder, "smoke.json");
   if (File.Exists(testMarker)) {
    var smoke = JsonSerializer.Deserialize<string[]>(File.ReadAllText(testMarker))!;
    info.ArgumentList.Add("--smoke"); info.ArgumentList.Add(smoke[0]); info.ArgumentList.Add(smoke[1]);
   }
   using var next = Process.Start(info) ?? throw new IOException("Falha ao abrir a nova versão.");
   for (int i = 0; i < 300; i++) {
    if (File.Exists(Path.Combine(folder, "started"))) {
     replaced = false; // A running, acknowledged version must not be rolled back for log/cleanup failures.
     File.WriteAllText(Path.Combine(folder, "state.json"), "{\"state\":\"completed\"}");
     try { File.Delete(source); } catch (IOException) { } catch (UnauthorizedAccessException) { }
     return 0;
    }
    if (next.HasExited) throw new IOException("A nova versão encerrou antes de iniciar.");
    await Task.Delay(100);
   }
   if (!next.HasExited) { next.Kill(); await next.WaitForExitAsync(); }
   throw new IOException("A nova versão não confirmou a abertura.");
  } catch (Exception error) {
   var state = "failed";
   if (replaced && backup != null && target != null) {
    try {
     var failed = ReadJob(path).Release.Sha256;
     File.WriteAllText(Path.Combine(ClientUpdates.UpdateRoot, "blocked-" + failed), "Falha ao iniciar; versão anterior preservada.");
    } catch { /* Failure to record a blocked release must not prevent recovery. */ }
    try {
     File.Replace(backup, target, target + ".failed-update");
     var previous = new ProcessStartInfo(target) { UseShellExecute = false };
     var marker = Path.Combine(folder!, "smoke.json");
     if(File.Exists(marker)){
      var smoke = JsonSerializer.Deserialize<string[]>(File.ReadAllText(marker))!;
      previous.ArgumentList.Add("--smoke");previous.ArgumentList.Add(smoke[0]);previous.ArgumentList.Add(smoke[1]+".rollback");
     }
     Process.Start(previous); state = "rolled-back";
    } catch { state = "recovery-required"; }
   }
   if (folder != null) File.WriteAllText(Path.Combine(folder, "state.json"), JsonSerializer.Serialize(new { state, error = error.GetType().Name }));
   return 1;
  }
 }
}
