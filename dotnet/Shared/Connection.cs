using System.Net;
using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;
using System.Text.Json;

namespace LocalAuthor.Connectivity;
record Connection(string Server,string CertificateSha256,string AccessKey,string DeviceId,string Name,int DiscoveryPort=38443,bool CanPublishUpdates=false) {
 public Uri Validate() {
  if(!Uri.TryCreate(Server,UriKind.Absolute,out var uri)||uri.Scheme!="https"||uri.UserInfo!=""||uri.Query!=""||uri.Fragment!=""||uri.AbsolutePath!="/"||!IPAddress.TryParse(uri.Host,out var ip)) throw new InvalidDataException("Arquivo de conexão inválido. Solicite um novo arquivo ao servidor.");
  var b=ip.GetAddressBytes();
  if(b.Length!=4||!(IPAddress.IsLoopback(ip)||b[0]==10||b[0]==172&&b[1]>=16&&b[1]<=31||b[0]==192&&b[1]==168)) throw new InvalidDataException("O endereço deve pertencer à rede local.");
  if(CertificateSha256.Length!=64||AccessKey.Length!=64||!CertificateSha256.All(Uri.IsHexDigit)||!AccessKey.All(Uri.IsHexDigit)) throw new InvalidDataException("Identificação da conexão inválida.");
  if(DiscoveryPort<1024||DiscoveryPort>65535)throw new InvalidDataException("Porta de descoberta inválida.");
  return uri;
 }
 public bool Matches(X509Certificate2 cert) => CryptographicOperations.FixedTimeEquals(cert.GetCertHash(HashAlgorithmName.SHA256),Convert.FromHexString(CertificateSha256)) && cert.NotBefore.ToUniversalTime()<=DateTime.UtcNow && cert.NotAfter.ToUniversalTime()>DateTime.UtcNow;
 public static Connection Parse(byte[] bytes) => JsonSerializer.Deserialize<Connection>(bytes,new JsonSerializerOptions{PropertyNameCaseInsensitive=true}) ?? throw new InvalidDataException("Arquivo vazio.");
 public static Connection Import(string path) {if(new FileInfo(path).Length>65536)throw new InvalidDataException("Arquivo de conexão grande demais.");var result=Parse(File.ReadAllBytes(path));result.Validate();return result;}
}
