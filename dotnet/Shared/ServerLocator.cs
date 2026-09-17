using System.Net;
using System.Security.Authentication;
namespace LocalAuthor.Connectivity;
static class ServerLocator {
 public static async Task<bool> ProbeAsync(Connection selected,CancellationToken cancel) {
  var uri=selected.Validate();
  using var handler=new HttpClientHandler{UseProxy=false,AllowAutoRedirect=false,ServerCertificateCustomValidationCallback=(_,cert,_,_)=>cert!=null&&selected.Matches(cert)};
  using var client=new HttpClient(handler){Timeout=TimeSpan.FromSeconds(2)};
  client.DefaultRequestHeaders.Authorization=new("Bearer",selected.AccessKey);
  try {
   using var health=await client.GetAsync(new Uri(uri,"/api/health"),cancel);
   if(health.StatusCode == HttpStatusCode.Unauthorized)throw new AuthenticationException("Acesso revogado ou não autorizado. Solicite uma conexão atualizada.");
   return health.IsSuccessStatusCode;
  }catch(HttpRequestException){return false;}catch(TaskCanceledException) when(!cancel.IsCancellationRequested){return false;}
 }
 public static async Task<Connection> ResolveAsync(Connection selected,Action<string> progress,CancellationToken cancel) {
  if(await ProbeAsync(selected,cancel))return selected;
  progress("Procurando seu servidor nesta rede…");
  foreach(var endpoint in (await LanDiscovery.FindAsync(selected.CertificateSha256,selected.DiscoveryPort,cancel)).Take(4)) {
   var candidate=selected with{Server=endpoint};
   if(await ProbeAsync(candidate,cancel))return candidate;
  }
  throw new HttpRequestException("Servidor não encontrado. Confira se os dois computadores estão na mesma rede e se o firewall permite a descoberta.");
 }
}
