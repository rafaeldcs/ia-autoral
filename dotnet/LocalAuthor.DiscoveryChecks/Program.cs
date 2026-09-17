using System.Net;
using System.Net.Sockets;
using System.Security.Authentication;
using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;
using System.Text.Json;
using LocalAuthor.Connectivity;

var checks=new List<string>();
void Check(string name,bool passed){if(!passed)throw new Exception(name);checks.Add(name);}
int Port(){using var s=new UdpClient(new IPEndPoint(IPAddress.Any,0));return ((IPEndPoint)s.Client.LocalEndPoint!).Port;}
var local=LanDiscovery.Interfaces().First();
Check("Public addresses are not discovery peers",!LanDiscovery.LocalPeer(IPAddress.Parse("8.8.8.8")));
Check("Current interface subnet is permitted",LanDiscovery.Allows(local.Address,local.Address));
Check("Broadcast address follows subnet prefix",LanDiscovery.Broadcast(IPAddress.Parse("192.168.2.31"),24).ToString()=="192.168.2.255");
Check("Invalid subnet prefix fails closed",!LanDiscovery.SameSubnet(local.Address,local.Address,0));
using var rsa=RSA.Create(2048);
var request=new CertificateRequest("CN=Discovery check",rsa,HashAlgorithmName.SHA256,RSASignaturePadding.Pkcs1);
var san=new SubjectAlternativeNameBuilder();san.AddIpAddress(IPAddress.Parse("127.0.0.2"));request.CertificateExtensions.Add(san.Build());
using var generated=request.CreateSelfSigned(DateTimeOffset.UtcNow.AddDays(-1),DateTimeOffset.UtcNow.AddDays(1));
using var cert=X509CertificateLoader.LoadPkcs12(generated.Export(X509ContentType.Pfx),null);
string fingerprint=cert.GetCertHashString(HashAlgorithmName.SHA256),key=Convert.ToHexString(RandomNumberGenerator.GetBytes(32));
int requests=0;bool revoked=false;
var builder=WebApplication.CreateBuilder();builder.Logging.ClearProviders();builder.WebHost.ConfigureKestrel(o=>o.Listen(local.Address,0,l=>l.UseHttps(cert)));
var app=builder.Build();app.MapGet("/api/health",(HttpContext c)=>{requests++;return c.Request.Headers.Authorization=="Bearer "+key&&!revoked?Results.Json(new{status="ok"}):Results.StatusCode(401);});
await app.StartAsync();int httpsPort=new Uri(app.Urls.Single()).Port;int discoveryPort=Port();
using var stop=new CancellationTokenSource();
var responder=LanDiscovery.RespondAsync(fingerprint,httpsPort,discoveryPort,stop.Token);
try {
 var connection=new Connection($"https://127.0.0.2:{httpsPort}",fingerprint,key,"test","Test",discoveryPort);
 Check("Direct pinned HTTPS fixture is reachable",await ServerLocator.ProbeAsync(connection with{Server=$"https://{local.Address}:{httpsPort}"},CancellationToken.None));
 var resolved=await ServerLocator.ResolveAsync(connection,_=>{},CancellationToken.None);
 Check("Stale IP is replaced by authenticated discovery result",resolved.Server==$"https://{local.Address}:{httpsPort}");
 Check("Certificate identity survives an IP/SAN change",await ServerLocator.ProbeAsync(resolved,CancellationToken.None));
 int before=requests;
 var wrong=resolved with{CertificateSha256=new string('0',64)};
 Check("Wrong TLS identity rejected before credentials reach HTTP endpoint",!await ServerLocator.ProbeAsync(wrong,CancellationToken.None)&&requests==before);
 Check("Other server fingerprints are ignored",(await LanDiscovery.FindAsync(new string('0',64),discoveryPort,CancellationToken.None)).Count==0);
 revoked=true;bool rejected=false;try{await ServerLocator.ResolveAsync(resolved,_=>{},CancellationToken.None);}catch(AuthenticationException){rejected=true;}
 Check("Revoked access does not bypass authentication via discovery",rejected);
 using(var udp=new UdpClient(new IPEndPoint(local.Address,0))){
  var query=JsonSerializer.SerializeToUtf8Bytes(new{protocol="localauthor-discovery-v1",fingerprint,nonce="not-valid"});await udp.SendAsync(query,new IPEndPoint(local.Address,discoveryPort));using var deadline=new CancellationTokenSource(400);bool ignored=false;try{await udp.ReceiveAsync(deadline.Token);}catch(OperationCanceledException){ignored=true;}Check("Malformed discovery nonce ignored",ignored);
 }
}finally{stop.Cancel();await responder;await app.StopAsync();await app.DisposeAsync();}
// An impostor's well-shaped response cannot select the server unless nonce and TLS identity match.
int fakePort=Port();using var fake=new UdpClient(new IPEndPoint(IPAddress.Any,fakePort));
var spoof=Task.Run(async()=>{var received=await fake.ReceiveAsync();var reply=JsonSerializer.SerializeToUtf8Bytes(new{protocol="localauthor-discovery-v1",nonce=new string('A',32),fingerprint,port=8443});await fake.SendAsync(reply,received.RemoteEndPoint);});
Check("Response with mismatched request nonce is ignored",(await LanDiscovery.FindAsync(fingerprint,fakePort,CancellationToken.None)).Count==0);await spoof;
Console.WriteLine(JsonSerializer.Serialize(new{passed=checks.Count,checks,physicalNetworkSwitchTested=false}));
