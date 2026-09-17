using System.Diagnostics;
using System.Reflection.PortableExecutable;
using System.Text.Json;
using LocalAuthor.Connectivity;

sealed class ReleaseConflictException : Exception;

static class ReleasePublisher {
 public static async Task<bool> PublishAsync(string root, Stream body, ClientRelease release, string actor, Func<bool> stillAuthorized, CancellationToken cancel) {
  var version = release.Validate();
  Directory.CreateDirectory(root);
  if ((File.GetAttributes(root) & FileAttributes.ReparsePoint) != 0) throw new IOException("Pasta inválida.");
  // Also held by the local publisher script; only one publication may change current.json.
  using var publicationLock = new FileStream(Path.Combine(root, "publish.lock"), FileMode.OpenOrCreate, FileAccess.ReadWrite, FileShare.None);
  var manifest = Path.Combine(root, "current.json");
  ClientRelease? current = File.Exists(manifest) ? JsonSerializer.Deserialize<ClientRelease>(File.ReadAllText(manifest), ClientRelease.Json) : null;
  if(current != null && current.Validate() >= version) {
   if(current.Validate() == version && current.Sha256 == release.Sha256 && current.Size == release.Size) return false;
   throw new ReleaseConflictException();
  }
  var pending = Path.Combine(root, Guid.NewGuid().ToString("N") + ".upload");
  var pendingManifest = pending + ".json";
  try {
   using(var file = new FileStream(pending, FileMode.CreateNew, FileAccess.Write, FileShare.None, 81920, true)) {
    var buffer = new byte[81920]; long total = 0; int count;
    while((count = await body.ReadAsync(buffer, cancel)) > 0) {
     total += count; if(total > release.Size) throw new InvalidDataException("Tamanho incorreto.");
     await file.WriteAsync(buffer.AsMemory(0,count), cancel);
    }
   }
   await release.VerifyAsync(pending, cancel);
   // Inspect metadata only. Uploaded executables are never run on the server.
   var info = FileVersionInfo.GetVersionInfo(pending);
   using(var file = File.OpenRead(pending)) using(var pe = new PEReader(file)) {
    if(pe.PEHeaders.CoffHeader.Machine != System.Reflection.PortableExecutable.Machine.Amd64 ||
       info.ProductName != "LocalAuthor.Client" || info.OriginalFilename != "LocalAuthor.Client.dll" ||
       !Version.TryParse(info.FileVersion, out var actual) || actual != version)
     throw new InvalidDataException("Selecione o executável do cliente LocalAuthor Windows x64, não o instalador.");
   }
   cancel.ThrowIfCancellationRequested();
   if(!stillAuthorized()) throw new UnauthorizedAccessException("Permissão revogada durante o envio.");
   var package = Path.Combine(root, release.Sha256 + ".exe");
   if(File.Exists(package)) { await release.VerifyAsync(package, cancel); File.Delete(pending); }
   else File.Move(pending, package);
   // This record documents validation/authorization; current.json determines the active release.
   File.WriteAllText(pendingManifest, JsonSerializer.Serialize(release));
   File.WriteAllText(Path.Combine(root,"publication-"+Guid.NewGuid().ToString("N")+".json"),
    JsonSerializer.Serialize(new { at=DateTimeOffset.UtcNow, deviceId=actor, action="validated-for-publication", release }));
   if(File.Exists(manifest)) File.Replace(pendingManifest, manifest, manifest+".previous");
   else File.Move(pendingManifest, manifest);
   return true;
  } finally {
   if(File.Exists(pending)) File.Delete(pending);
   if(File.Exists(pendingManifest)) File.Delete(pendingManifest);
  }
 }
}
