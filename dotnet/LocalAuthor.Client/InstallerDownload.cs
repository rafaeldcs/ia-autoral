using System.Security.Cryptography;
using System.Text.Json;
using LocalAuthor.Connectivity;

namespace LocalAuthor.Client;

internal static class InstallerDownload
{
 internal static bool Allows(string value,Uri origin) => Uri.TryCreate(value,UriKind.Absolute,out var uri) &&
  uri.Scheme=="https" && uri.Scheme==origin.Scheme && uri.Host==origin.Host && uri.Port==origin.Port &&
  uri.UserInfo.Length==0 && uri.AbsolutePath=="/api/app/installer/file" && uri.Query.Length==0 && uri.Fragment.Length==0;

 internal static async Task SaveAsync(Connection connection,string profileCookie,string destination,CancellationToken cancel){
  using var client=ClientUpdates.CreateClient(connection);
  client.DefaultRequestHeaders.Add("Cookie","la_profile="+profileCookie);
  using var info=await client.GetAsync("/api/app/installer",HttpCompletionOption.ResponseHeadersRead,cancel);info.EnsureSuccessStatusCode();
  using var metadataStream=await info.Content.ReadAsStreamAsync(cancel);var buffer=new byte[4097];int used=0,count;
  while(used<buffer.Length&&(count=await metadataStream.ReadAsync(buffer.AsMemory(used),cancel))>0)used+=count;
  if(used>4096)throw new InvalidDataException("Manifesto grande demais.");
  using var document=JsonDocument.Parse(buffer.AsMemory(0,used));var data=document.RootElement;
  if(!data.GetProperty("available").GetBoolean())throw new InvalidDataException("Instalador não publicado.");
  var hash=data.GetProperty("sha256").GetString()!;var size=data.GetProperty("size").GetInt64();
  if(hash.Length!=64||!hash.All(Uri.IsHexDigit)||size<1||size>500_000_000)throw new InvalidDataException("Publicação inválida.");
  var parent=Path.GetDirectoryName(Path.GetFullPath(destination))!;UpdateInstaller.RejectLinks(parent);
  if(File.Exists(destination)&&(File.GetAttributes(destination)&FileAttributes.ReparsePoint)!=0)throw new IOException("Destino não pode ser um link.");
  var pending=Path.Combine(parent,Guid.NewGuid().ToString("N")+".downloading");
  try{
   using var response=await client.GetAsync("/api/app/installer/file",HttpCompletionOption.ResponseHeadersRead,cancel);response.EnsureSuccessStatusCode();
   if(response.Content.Headers.ContentLength!=size||!response.Headers.TryGetValues("X-Content-Sha256",out var checksum)||checksum.Single()!=hash)throw new InvalidDataException("Publicação mudou; tente novamente.");
   using(var input=await response.Content.ReadAsStreamAsync(cancel))
   using(var output=new FileStream(pending,FileMode.CreateNew,FileAccess.Write,FileShare.None,81920,true)){
    var block=new byte[81920];long total=0;
    while((count=await input.ReadAsync(block,cancel))>0){total+=count;if(total>size)throw new InvalidDataException("Tamanho inválido.");await output.WriteAsync(block.AsMemory(0,count),cancel);}
    if(total!=size)throw new InvalidDataException("Download incompleto.");
   }
   using(var verified=File.OpenRead(pending))if(Convert.ToHexString(await SHA256.HashDataAsync(verified,cancel))!=hash)throw new InvalidDataException("Integridade inválida.");
   File.Move(pending,destination,true);
  }finally{if(File.Exists(pending))File.Delete(pending);}
 }
}
