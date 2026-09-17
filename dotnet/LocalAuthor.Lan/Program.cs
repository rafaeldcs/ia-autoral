using System.Net;
using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;
using System.Text;
using System.Text.Json;
using LocalAuthor.Connectivity;

var argsList = args.ToList();
string Option(string name, string fallback) { var i=argsList.IndexOf(name); return i>=0 && i+1<argsList.Count ? argsList[i+1] : fallback; }
var data = Path.GetFullPath(Option("--data", Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "LocalAuthor", "lan")));
Directory.CreateDirectory(data);
var configFile=Path.Combine(data,"server.json");
var devicesFile=Path.Combine(data,"devices.json");
var json = new JsonSerializerOptions { WriteIndented=true, PropertyNameCaseInsensitive=true };
void Save<T>(string path,T value) { var temp=path+".tmp"; File.WriteAllText(temp,JsonSerializer.Serialize(value,json)); File.Move(temp,path,true); }
T Read<T>(string path) => JsonSerializer.Deserialize<T>(File.ReadAllText(path),json) ?? throw new InvalidDataException("Arquivo inválido.");
try {
 var command=args.FirstOrDefault() ?? "serve";
 if(command=="init") {
  if(File.Exists(configFile)) throw new InvalidOperationException("Servidor já configurado. Preserve o certificado e os dispositivos existentes.");
  var ip=IPAddress.Parse(Option("--bind","127.0.0.1"));
  if(!NetworkRules.IsPrivate(ip) && !IPAddress.IsLoopback(ip)) throw new InvalidOperationException("Escolha um IPv4 da rede local.");
  int port=int.Parse(Option("--port","8443")), backend=int.Parse(Option("--backend-port","8765"));
  if(port<1024||port>65535||backend<1024||backend>65535) throw new InvalidOperationException("Porta inválida.");
  var prefix=int.Parse(Option("--prefix","24")); if(prefix<8||prefix>32) throw new InvalidOperationException("Prefixo IPv4 inválido.");
  using var rsa=RSA.Create(3072);
  var request=new CertificateRequest("CN=LocalAuthor LAN",rsa,HashAlgorithmName.SHA256,RSASignaturePadding.Pkcs1);
  var san=new SubjectAlternativeNameBuilder();san.AddIpAddress(ip);request.CertificateExtensions.Add(san.Build());
  request.CertificateExtensions.Add(new X509BasicConstraintsExtension(false,false,0,true));
  request.CertificateExtensions.Add(new X509KeyUsageExtension(X509KeyUsageFlags.DigitalSignature|X509KeyUsageFlags.KeyEncipherment,true));
  request.CertificateExtensions.Add(new X509EnhancedKeyUsageExtension(new OidCollection{new Oid("1.3.6.1.5.5.7.3.1")},false));
  using var cert=request.CreateSelfSigned(DateTimeOffset.UtcNow.AddMinutes(-5),DateTimeOffset.UtcNow.AddYears(1));
  File.WriteAllBytes(Path.Combine(data,"server.pfx"),cert.Export(X509ContentType.Pfx));
  File.WriteAllBytes(Path.Combine(data,"server.cer"),cert.Export(X509ContentType.Cert));
  Save(configFile,new LanConfig(ip.ToString(),prefix,port,backend,Path.GetFullPath(Option("--home",Path.GetDirectoryName(data)!)),cert.GetCertHashString(HashAlgorithmName.SHA256),argsList.Contains("--discover")));
  Save(devicesFile,new List<Device>());
  Console.WriteLine("Servidor configurado. Adicione um dispositivo antes de conectar.");return;
 }
 var config=Read<LanConfig>(configFile);
 var address=IPAddress.Parse(config.Bind);
 if(!NetworkRules.IsPrivate(address)&&!IPAddress.IsLoopback(address)) throw new InvalidDataException("Bind fora da rede local.");
 if(command=="add-device") {
  var destination=Path.GetFullPath(Option("--output",Path.Combine(data,"conexao.localauthor")));
  if(File.Exists(destination)) throw new InvalidOperationException("O arquivo de conexão já existe; escolha outro nome.");
  var key=Convert.ToHexString(RandomNumberGenerator.GetBytes(32));
  var role=Option("--role","client");if(role is not ("client" or "publisher"))throw new InvalidDataException("Permissão inválida.");
  var device=new Device(Guid.NewGuid().ToString("N"),Option("--name","Meu computador"),Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(key))),true,role);
  var devices=Read<List<Device>>(devicesFile);devices.Add(device);Save(devicesFile,devices);
  var advertised=config.AutoDiscover?LanDiscovery.Interfaces().Select(n=>n.Address.ToString()).FirstOrDefault()??config.Bind:config.Bind;
  Save(destination,new {Server=$"https://{advertised}:{config.Port}",CertificateSha256=config.CertificateSha256,AccessKey=key,DeviceId=device.Id,Name=device.Name,DiscoveryPort=config.DiscoveryPort,CanPublishUpdates=role=="publisher"});
  Console.WriteLine($"Dispositivo: {device.Id}\nConexão privada criada em: {destination}");return;
 }
 if(command=="revoke") {
  var id=Option("--id","");var devices=Read<List<Device>>(devicesFile);
  if(!devices.Any(d=>d.Id==id)) throw new InvalidOperationException("Dispositivo não encontrado.");
  Save(devicesFile,devices.Select(d=>d.Id==id ? d with {Enabled=false} : d).ToList());Console.WriteLine("Acesso revogado.");return;
 }
 if(command=="list") { foreach(var d in Read<List<Device>>(devicesFile)) Console.WriteLine($"{d.Id} | {d.Name} | {(d.Enabled?"ativo":"revogado")} | {d.Role}");return; }
 if(command!="serve") throw new InvalidOperationException("Use init, add-device, revoke, list ou serve.");
 using var certificate=X509CertificateLoader.LoadPkcs12FromFile(Path.Combine(data,"server.pfx"),null);
 if(certificate.GetCertHashString(HashAlgorithmName.SHA256)!=config.CertificateSha256 || certificate.NotAfter.ToUniversalTime()<DateTime.UtcNow) throw new InvalidDataException("Certificado divergente ou vencido.");
 var upstreamToken=File.ReadAllText(Path.Combine(config.BackendHome,"api.token")).Trim();
 if(upstreamToken.Length<32) throw new InvalidDataException("Token local inválido.");
 var builder=WebApplication.CreateBuilder();
 builder.Logging.ClearProviders();
 builder.WebHost.ConfigureKestrel(options=>{
  options.Limits.MaxRequestBodySize=2_500_000;options.Limits.MaxConcurrentConnections=32;
  options.Limits.RequestHeadersTimeout=TimeSpan.FromSeconds(10);
  options.Listen(config.AutoDiscover?IPAddress.Any:address,config.Port,listen=>listen.UseHttps(certificate));
 });
 var app=builder.Build();
 var publicationPassword=new PublicationPasswordStore(Path.Combine(data,"publication-auth.sqlite3"));
 using var discoveryCancel=new CancellationTokenSource();
 var discoveryTask=config.AutoDiscover?LanDiscovery.RespondAsync(config.CertificateSha256,config.Port,config.DiscoveryPort,discoveryCancel.Token):Task.CompletedTask;
 app.Lifetime.ApplicationStopping.Register(()=>discoveryCancel.Cancel());
 _=discoveryTask.ContinueWith(t=>{if(t.IsFaulted){Console.Error.WriteLine("Descoberta indisponível; verifique a porta UDP.");app.Lifetime.StopApplication();}},TaskScheduler.Default);
 using var client=new HttpClient(new HttpClientHandler {AllowAutoRedirect=false,UseProxy=false}) {BaseAddress=new Uri($"http://127.0.0.1:{config.BackendPort}"),Timeout=TimeSpan.FromSeconds(120)};
 using var concurrency=new SemaphoreSlim(4,4);
 var advertisedOrigin=$"https://{config.Bind}:{config.Port}";
 var staticPaths=new HashSet<string>{"/","/chat.js","/chat.css","/advanced","/app.js","/styles.css"};
 app.Run(async context=>{
  context.Response.Headers.CacheControl="no-store";context.Response.Headers.XContentTypeOptions="nosniff";
  async Task Error(int code,string message){context.Response.StatusCode=code;await context.Response.WriteAsJsonAsync(new{error=message});}
  var remote=context.Connection.RemoteIpAddress;
  var local=context.Connection.LocalIpAddress;
  if(remote is null || (config.AutoDiscover?(local is null||!LanDiscovery.Allows(local,remote)):!NetworkRules.SameSubnet(remote,address,config.Prefix))) {await Error(403,"Acesso restrito à rede configurada.");return;}
  var authority=$"{(config.AutoDiscover?local:address)}:{config.Port}";var origin=$"https://{authority}";
  if(!string.Equals(context.Request.Host.Value,authority,StringComparison.OrdinalIgnoreCase)) {await Error(400,"Endereço não autorizado.");return;}
  if(context.Request.Headers.Origin.Count>0 && context.Request.Headers.Origin.ToString()!=origin) {await Error(403,"Origem não autorizada.");return;}
  if(context.Request.Headers["Sec-Fetch-Site"].ToString() is "cross-site" or "same-site") {await Error(403,"Origem não autorizada.");return;}
  if(context.Request.Method is not ("GET" or "POST")) {await Error(405,"Método não permitido.");return;}
  var path=context.Request.Path.Value ?? "/";
  bool publicAsset=context.Request.Method=="GET" && staticPaths.Contains(path);
  string accessKey="";
  Device? authenticated=null;
  if(!publicAsset) {
   var auth=context.Request.Headers.Authorization.ToString();
   if(!auth.StartsWith("Bearer ",StringComparison.Ordinal)||auth.Length!=71) {await Error(401,"Conexão não autorizada. Importe uma conexão fornecida pelo servidor.");return;}
   accessKey=auth[7..];var hash=SHA256.HashData(Encoding.UTF8.GetBytes(accessKey));
   List<Device> devices;
   try {devices=Read<List<Device>>(devicesFile);} catch {await Error(503,"Cadastro de dispositivos indisponível.");return;}
   authenticated=devices.FirstOrDefault(d=>d.Enabled&&CryptographicOperations.FixedTimeEquals(Convert.FromHexString(d.KeyHash),hash));
   if(authenticated==null) {await Error(401,"Acesso inválido ou revogado.");return;}
   if(!path.StartsWith("/api/",StringComparison.Ordinal)) {await Error(404,"Rota não encontrada.");return;}
  }
  if(!await concurrency.WaitAsync(0)){await Error(429,"Servidor ocupado. Tente novamente em instantes.");return;}
  try {
   if(path=="/api/device" && context.Request.Method=="GET") {
    await context.Response.WriteAsJsonAsync(new {canPublishUpdates=true,publicationPasswordConfigured=publicationPassword.Configured,publicationPasswordRequired=true});return;
   }
   if(path=="/api/publication-password" && context.Request.Method=="POST") {
    if(context.Request.ContentLength is null or <1 or >4096 || context.Request.ContentType?.Split(';')[0]!="application/json"){await Error(400,"Envie uma senha válida.");return;}
    try{
     using var document=await JsonDocument.ParseAsync(context.Request.Body,cancellationToken:context.RequestAborted);
     var password=document.RootElement.GetProperty("password").GetString()??"";
     if(publicationPassword.Configured){await Error(409,"A senha já foi cadastrada neste servidor.");return;}
     if(!publicationPassword.SetOnce(password)){await Error(409,"A senha já foi cadastrada neste servidor.");return;}
     await context.Response.WriteAsJsonAsync(new{configured=true});
    }catch(Exception e) when(e is JsonException or KeyNotFoundException or InvalidOperationException or InvalidDataException){await Error(400,"Use uma senha de 12 a 256 caracteres.");}
    return;
   }
   if(path=="/api/client-update/publish") {
    if(context.Request.Method!="POST"){await Error(405,"Use POST.");return;}
    string password;
    try{var encoded=context.Request.Headers["X-Publication-Password"].ToString();if(encoded.Length>2048)throw new FormatException();password=new UTF8Encoding(false,true).GetString(Convert.FromBase64String(encoded));}catch{await Error(403,"Informe a senha de publicação.");return;}
    var passwordResult=publicationPassword.Verify(authenticated!.Id,password);
    if(passwordResult!=PasswordCheck.Accepted){
     if(passwordResult==PasswordCheck.Locked){context.Response.Headers.RetryAfter="60";await Error(429,"Muitas tentativas. Aguarde um minuto.");}
     else if(passwordResult==PasswordCheck.NotConfigured)await Error(428,"Cadastre a senha de publicação na primeira abertura do aplicativo.");
     else await Error(403,"Senha de publicação incorreta.");return;
    }
    var size=context.Request.ContentLength;
    if(size is null or <1 or >ClientRelease.MaxSize || context.Request.ContentType!="application/octet-stream") {await Error(400,"Envie um executável com tamanho válido.");return;}
    var release=new ClientRelease(context.Request.Headers["X-Release-Version"].ToString(),context.Request.Headers["X-Release-Sha256"].ToString().ToUpperInvariant(),size.Value);
    try {release.Validate();}catch {await Error(400,"Versão ou hash inválido.");return;}
    var bodyLimit=context.Features.Get<Microsoft.AspNetCore.Http.Features.IHttpMaxRequestBodySizeFeature>();
    if(bodyLimit!=null)bodyLimit.MaxRequestBodySize=ClientRelease.MaxSize;
    using var deadline=CancellationTokenSource.CreateLinkedTokenSource(context.RequestAborted);deadline.CancelAfter(TimeSpan.FromMinutes(5));
    bool AuthorizedNow()=>Read<List<Device>>(devicesFile).Any(d=>d.Id==authenticated.Id&&d.Enabled&&d.KeyHash==authenticated.KeyHash);
    try {
     var published=await ReleasePublisher.PublishAsync(Path.Combine(data,"client-releases"),context.Request.Body,release,authenticated.Id,AuthorizedNow,deadline.Token);
     await context.Response.WriteAsJsonAsync(new{published,version=release.Version});
    }catch(ReleaseConflictException){await Error(409,"Publique uma versão maior. Esta versão já existe com outro conteúdo.");}
     catch(UnauthorizedAccessException){await Error(403,"Permissão revogada durante a publicação.");}
     catch(InvalidDataException){await Error(400,"Pacote inválido: confira executável, versão, tamanho e hash.");}
     catch(BadImageFormatException){await Error(400,"O arquivo não é um executável compatível.");}
     catch(IOException){await Error(503,"Publicação ocupada ou armazenamento indisponível. Tente novamente.");}
    return;
   }
   if(context.Request.Method=="GET" && (path=="/api/client-update"||path=="/api/client-update/package")) {
    var releases=Path.Combine(data,"client-releases");
    if(path=="/api/client-update") {
     var manifest=Path.Combine(releases,"current.json");
     if(!File.Exists(manifest)){await Error(404,"Nenhuma atualização publicada.");return;}
     var release=Read<ClientRelease>(manifest);release.Validate();
     await context.Response.WriteAsJsonAsync(release);return;
    }
    var hash=context.Request.Query["sha256"].ToString();
    if(hash.Length!=64||!hash.All(Uri.IsHexDigit)){await Error(400,"Publicação inválida.");return;}
    var package=Path.Combine(releases,hash.ToUpperInvariant()+".exe");
    if(!File.Exists(package)){await Error(404,"Publicação não encontrada.");return;}
    var file=new FileInfo(package);
    if(file.Length<1||file.Length>ClientRelease.MaxSize||(file.Attributes&FileAttributes.ReparsePoint)!=0){await Error(503,"Publicação indisponível.");return;}
    context.Response.ContentType="application/octet-stream";context.Response.ContentLength=file.Length;
    await context.Response.SendFileAsync(package,context.RequestAborted);return;
   }
   using var request=new HttpRequestMessage(new HttpMethod(context.Request.Method),path+context.Request.QueryString);
   request.Headers.Authorization=new System.Net.Http.Headers.AuthenticationHeaderValue("Bearer",upstreamToken);
   if(context.Request.Method=="POST") {
    if(context.Request.ContentLength is null or >2_500_000 || context.Request.ContentLength<=0 || context.Request.ContentType?.Split(';')[0]!="application/json") {await Error(400,"Envie JSON com tamanho válido.");return;}
    using var reader=new StreamReader(context.Request.Body,Encoding.UTF8,false,4096,true);var body=await reader.ReadToEndAsync(context.RequestAborted);
    if(accessKey.Length>0 && body.Contains(accessKey,StringComparison.Ordinal)) {await Error(400,"Não envie a chave de conexão em mensagens.");return;}
    request.Content=new StringContent(body,Encoding.UTF8,"application/json");
   }
   using var response=await client.SendAsync(request,HttpCompletionOption.ResponseHeadersRead,context.RequestAborted);
   context.Response.StatusCode=(int)response.StatusCode;
   foreach(var name in new[]{"Content-Security-Policy","Referrer-Policy","X-Content-Type-Options"})
    if(response.Headers.TryGetValues(name,out var values)) context.Response.Headers[name]=values.ToArray();
   context.Response.ContentType=response.Content.Headers.ContentType?.ToString() ?? "application/json";
   await response.Content.CopyToAsync(context.Response.Body,context.RequestAborted);
  } catch(OperationCanceledException) {if(!context.Response.HasStarted) await Error(504,"O servidor demorou a responder.");}
    catch(HttpRequestException) {if(!context.Response.HasStarted) await Error(503,"A IA local está desligada. Inicie o servidor neste computador.");}
    finally {concurrency.Release();}
 });
 Console.WriteLine($"LocalAuthor LAN em {advertisedOrigin}; descoberta automática: {config.AutoDiscover}; backend em loopback.");
 await app.RunAsync();
} catch(Exception e) { Console.Error.WriteLine("Não foi possível iniciar: "+e.Message);Environment.ExitCode=1; }

record LanConfig(string Bind,int Prefix,int Port,int BackendPort,string BackendHome,string CertificateSha256,bool AutoDiscover=false,int DiscoveryPort=38443);
record Device(string Id,string Name,string KeyHash,bool Enabled,string Role="client");
static class NetworkRules {
 public static bool IsPrivate(IPAddress ip) {var b=ip.GetAddressBytes();return b.Length==4&&(b[0]==10||b[0]==172&&b[1]>=16&&b[1]<=31||b[0]==192&&b[1]==168);}
 public static bool SameSubnet(IPAddress remote,IPAddress local,int prefix) {
  if(remote.IsIPv4MappedToIPv6)remote=remote.MapToIPv4();var a=remote.GetAddressBytes();var b=local.GetAddressBytes();
  if(a.Length!=4||b.Length!=4||prefix<8||prefix>32)return false;
  if(!IsPrivate(remote)&&!IPAddress.IsLoopback(local))return false;
  for(int i=0;i<4;i++){int bits=Math.Clamp(prefix-i*8,0,8);int mask=bits==0?0:255<<(8-bits);if((a[i]&mask)!=(b[i]&mask))return false;}return true;
 }
}
