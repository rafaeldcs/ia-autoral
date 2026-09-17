using System.Net;
using System.Net.NetworkInformation;
using System.Net.Sockets;
using System.Security.Cryptography;
using System.Text.Json;
namespace LocalAuthor.Connectivity;
static class LanDiscovery {
 public const int DefaultPort=38443;
 public static bool IsPrivate(IPAddress ip) {var b=ip.GetAddressBytes();return b.Length==4&&(b[0]==10||b[0]==172&&b[1]>=16&&b[1]<=31||b[0]==192&&b[1]==168);}
 public static IEnumerable<(IPAddress Address,int Prefix)> Interfaces() => NetworkInterface.GetAllNetworkInterfaces().Where(n=>n.OperationalStatus==OperationalStatus.Up && n.NetworkInterfaceType is not (NetworkInterfaceType.Loopback or NetworkInterfaceType.Tunnel)).OrderByDescending(n=>n.GetIPProperties().GatewayAddresses.Count>0).SelectMany(n=>n.GetIPProperties().UnicastAddresses).Where(a=>IsPrivate(a.Address)).Select(a=>(a.Address,a.PrefixLength));
 public static bool SameSubnet(IPAddress a,IPAddress b,int prefix) {
  var x=a.GetAddressBytes();var y=b.GetAddressBytes();if(x.Length!=4||y.Length!=4||prefix<8||prefix>32)return false;
  for(int i=0;i<4;i++){int bits=Math.Clamp(prefix-i*8,0,8),mask=bits==0?0:255<<(8-bits);if((x[i]&mask)!=(y[i]&mask))return false;}return true;
 }
 public static bool LocalPeer(IPAddress remote) => IsPrivate(remote)&&Interfaces().Any(n=>SameSubnet(remote,n.Address,n.Prefix));
 public static bool Allows(IPAddress local,IPAddress remote) => IsPrivate(remote)&&Interfaces().Any(n=>n.Address.Equals(local)&&SameSubnet(remote,local,n.Prefix));
 public static IPAddress Broadcast(IPAddress address,int prefix) {var b=address.GetAddressBytes();for(int i=0;i<4;i++){int bits=Math.Clamp(prefix-i*8,0,8);b[i]=(byte)(b[i]|(255>>bits));}return new IPAddress(b);}
 public static async Task RespondAsync(string fingerprint,int httpsPort,int discoveryPort,CancellationToken cancel) {
  using var udp=new UdpClient(new IPEndPoint(IPAddress.Any,discoveryPort));var budget=new Queue<DateTime>();
  while(!cancel.IsCancellationRequested) {
   try {
    var packet=await udp.ReceiveAsync(cancel);if(packet.Buffer.Length>512||!LocalPeer(packet.RemoteEndPoint.Address))continue;
    using var doc=JsonDocument.Parse(packet.Buffer);var root=doc.RootElement;
    if(root.GetProperty("protocol").GetString()!="localauthor-discovery-v1"||root.GetProperty("fingerprint").GetString()!=fingerprint)continue;
    var nonce=root.GetProperty("nonce").GetString();if(nonce is null||nonce.Length!=32||!nonce.All(Uri.IsHexDigit))continue;
    var now=DateTime.UtcNow;while(budget.Count>0&&(now-budget.Peek()).TotalSeconds>1)budget.Dequeue();if(budget.Count>=20)continue;budget.Enqueue(now);
    var reply=JsonSerializer.SerializeToUtf8Bytes(new{protocol="localauthor-discovery-v1",nonce,fingerprint,port=httpsPort});await udp.SendAsync(reply,packet.RemoteEndPoint,cancel);
   }catch(OperationCanceledException){break;}catch(JsonException){}catch(KeyNotFoundException){}catch(InvalidOperationException){}catch(SocketException){if(!cancel.IsCancellationRequested)await Task.Delay(200,cancel);}
  }
 }
 public static async Task<List<string>> FindAsync(string fingerprint,int port,CancellationToken cancel) {
  var nonce=Convert.ToHexString(RandomNumberGenerator.GetBytes(16));var packet=JsonSerializer.SerializeToUtf8Bytes(new{protocol="localauthor-discovery-v1",nonce,fingerprint});
  using var udp=new UdpClient(new IPEndPoint(IPAddress.Any,0)){EnableBroadcast=true};
  var targets=Interfaces().SelectMany(n=>new[]{Broadcast(n.Address,n.Prefix),n.Address}).Distinct().ToArray();
  foreach(var target in targets)try{await udp.SendAsync(packet,new IPEndPoint(target,port),cancel);}catch(SocketException){}
  var found=new HashSet<string>();using var deadline=CancellationTokenSource.CreateLinkedTokenSource(cancel);deadline.CancelAfter(TimeSpan.FromSeconds(2));
  while(found.Count<8&&!deadline.IsCancellationRequested) {
   try {
    var response=await udp.ReceiveAsync(deadline.Token);if(response.Buffer.Length>512||response.RemoteEndPoint.Port!=port||!LocalPeer(response.RemoteEndPoint.Address))continue;
    using var doc=JsonDocument.Parse(response.Buffer);var root=doc.RootElement;
    if(root.GetProperty("protocol").GetString()!="localauthor-discovery-v1"||root.GetProperty("nonce").GetString()!=nonce||root.GetProperty("fingerprint").GetString()!=fingerprint)continue;
    int httpsPort=root.GetProperty("port").GetInt32();if(httpsPort<1024||httpsPort>65535)continue;found.Add($"https://{response.RemoteEndPoint.Address}:{httpsPort}");
   }catch(OperationCanceledException){break;}catch(JsonException){}catch(KeyNotFoundException){}catch(InvalidOperationException){}catch(FormatException){}
  }
  return found.ToList();
 }
}
