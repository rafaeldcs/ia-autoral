using System.Security.Cryptography;
using System.Text.Json;
namespace LocalAuthor.Connectivity;

record ClientRelease(string Version, string Sha256, long Size) {
 public const long MaxSize = 300L * 1024 * 1024;
 public static readonly JsonSerializerOptions Json = new() { PropertyNameCaseInsensitive = true };
 public Version Validate() {
  if (!System.Version.TryParse(Version, out var version) || version.Major < 0 ||
      Sha256.Length != 64 || !Sha256.All(Uri.IsHexDigit) || Size < 1 || Size > MaxSize)
   throw new InvalidDataException("Publicação de atualização inválida.");
  return version;
 }
 public async Task VerifyAsync(string path, CancellationToken cancel = default) {
  Validate();
  using var file = File.OpenRead(path);
  if (file.Length != Size || !Convert.ToHexString(await SHA256.HashDataAsync(file, cancel)).Equals(Sha256, StringComparison.OrdinalIgnoreCase))
   throw new InvalidDataException("O download da atualização está incompleto ou foi alterado.");
 }
}
