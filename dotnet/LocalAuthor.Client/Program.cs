using System.Diagnostics;
using System.Net;
using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;
using System.Text.Json;
using Microsoft.Web.WebView2.Core;
using Microsoft.Web.WebView2.WinForms;

namespace LocalAuthor.Client;
static class Program {
 [STAThread] static void Main(string[] args) {
  ApplicationConfiguration.Initialize();Application.Run(new ClientForm(args));
 }
}
record Connection(string Server,string CertificateSha256,string AccessKey,string DeviceId,string Name) {
 public Uri Validate() {
  if(!Uri.TryCreate(Server,UriKind.Absolute,out var uri)||uri.Scheme!="https"||uri.UserInfo!=""||uri.Query!=""||uri.Fragment!=""||uri.AbsolutePath!="/"||!IPAddress.TryParse(uri.Host,out var ip)) throw new InvalidDataException("Arquivo de conexão inválido. Solicite um novo arquivo ao servidor.");
  var b=ip.GetAddressBytes();
  if(b.Length!=4||!(IPAddress.IsLoopback(ip)||b[0]==10||b[0]==172&&b[1]>=16&&b[1]<=31||b[0]==192&&b[1]==168)) throw new InvalidDataException("O endereço deve pertencer à rede local.");
  if(CertificateSha256.Length!=64||AccessKey.Length!=64||!CertificateSha256.All(Uri.IsHexDigit)||!AccessKey.All(Uri.IsHexDigit)) throw new InvalidDataException("Identificação da conexão inválida.");
  return uri;
 }
 public bool Matches(X509Certificate2 cert) => CryptographicOperations.FixedTimeEquals(cert.GetCertHash(HashAlgorithmName.SHA256),Convert.FromHexString(CertificateSha256)) && cert.NotBefore.ToUniversalTime()<=DateTime.UtcNow && cert.NotAfter.ToUniversalTime()>DateTime.UtcNow;
 public static Connection Parse(byte[] bytes) => JsonSerializer.Deserialize<Connection>(bytes,new JsonSerializerOptions{PropertyNameCaseInsensitive=true}) ?? throw new InvalidDataException("Arquivo vazio.");
 public static Connection Import(string path) {if(new FileInfo(path).Length>65536)throw new InvalidDataException("Arquivo de conexão grande demais.");var result=Parse(File.ReadAllBytes(path));result.Validate();return result;}
}
sealed class ClientForm : Form {
 readonly string home=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"LocalAuthorClient");
 readonly Label status=new(){AutoSize=true,Text="Importe o arquivo de conexão criado no servidor.",Margin=new Padding(12)};
 readonly Button import=new(){Text="Conectar ao servidor…",AutoSize=true,Height=36};
 readonly Button reconnect=new(){Text="Reconectar",AutoSize=true,Height=36};
 readonly Button forget=new(){Text="Esquecer conexão",AutoSize=true,Height=36};
 readonly Panel content=new(){Dock=DockStyle.Fill};
 WebView2? browser;Connection? connection;bool connecting;
 readonly string? smokeFile;readonly string? reportFile;
 public ClientForm(string[] args) {
  Text="LocalAuthor — IA da sua rede";Width=1280;Height=880;MinimumSize=new Size(700,550);StartPosition=FormStartPosition.CenterScreen;
  Font=new Font("Segoe UI",10);BackColor=Color.White;
  var top=new FlowLayoutPanel{Dock=DockStyle.Top,AutoSize=true,Padding=new Padding(8),WrapContents=true};top.Controls.AddRange([import,reconnect,forget,status]);
  content.Controls.Add(new Label{Dock=DockStyle.Fill,Text="Sua IA, em outros computadores.\n\nNo servidor, crie um arquivo de conexão para este dispositivo.\nClique em Conectar ao servidor e selecione esse arquivo.\n\nProjetos e conversas continuam armazenados no servidor.",TextAlign=ContentAlignment.MiddleCenter,Font=new Font("Segoe UI",16)});
  Controls.Add(content);Controls.Add(top);Directory.CreateDirectory(home);
  int i=Array.IndexOf(args,"--smoke");if(i>=0){smokeFile=args[i+1];reportFile=args[i+2];Opacity=0;ShowInTaskbar=false;}
  import.Click+=async (_,_)=>{using var picker=new OpenFileDialog{Title="Escolha sua conexão privada",Filter="Conexão LocalAuthor|*.localauthor"};if(picker.ShowDialog(this)==DialogResult.OK)await ConnectFile(picker.FileName);};
  reconnect.Click+=async (_,_)=>{if(connection!=null)await Connect(connection);else await LoadSaved();};
  forget.Click+=(_,_)=>{if(MessageBox.Show(this,"Remover a conexão salva neste computador? Os projetos permanecem no servidor.","Esquecer conexão",MessageBoxButtons.YesNo,MessageBoxIcon.Question)!=DialogResult.Yes)return;File.Delete(Path.Combine(home,"connection.bin"));connection=null;browser?.Dispose();browser=null;status.Text="Conexão removida. Importe outra para continuar.";};
  Shown+=async (_,_)=>{if(smokeFile!=null)await ConnectFile(smokeFile);else await LoadSaved();};
 }
 async Task LoadSaved(){try{var file=Path.Combine(home,"connection.bin");if(File.Exists(file))await Connect(Connection.Parse(ProtectedData.Unprotect(File.ReadAllBytes(file),null,DataProtectionScope.CurrentUser)));}catch{status.Text="Não foi possível ler a conexão. Importe o arquivo novamente.";}}
 async Task ConnectFile(string path){try{await Connect(Connection.Import(path));}catch(Exception e){await Failure(e);}}
 async Task Failure(Exception error) {
  status.Text="Não foi possível conectar. Confira se o servidor está ligado e na mesma rede.";
  if(reportFile!=null){await File.WriteAllTextAsync(reportFile,JsonSerializer.Serialize(new{passed=false,error=error.GetType().Name}));Environment.ExitCode=1;Close();}
  else MessageBox.Show(this,error is HttpRequestException ? "Conexão recusada, certificado diferente ou acesso revogado. Confira o servidor e importe uma conexão atualizada." : error.Message,"LocalAuthor",MessageBoxButtons.OK,MessageBoxIcon.Information);
 }
 async Task Connect(Connection selected) {
  if(connecting)return;connecting=true;import.Enabled=reconnect.Enabled=forget.Enabled=false;
  try {
   var uri=selected.Validate();status.Text="Verificando servidor e identidade…";
   using var handler=new HttpClientHandler{UseProxy=false,AllowAutoRedirect=false,ServerCertificateCustomValidationCallback=(_,cert,_,_)=>cert!=null&&selected.Matches(cert)};
   using var client=new HttpClient(handler){Timeout=TimeSpan.FromSeconds(10)};
   client.DefaultRequestHeaders.Authorization=new("Bearer",selected.AccessKey);
   using var health=await client.GetAsync(new Uri(uri,"/api/health"));health.EnsureSuccessStatusCode();
   connection=selected;
   if(smokeFile==null) File.WriteAllBytes(Path.Combine(home,"connection.bin"),ProtectedData.Protect(JsonSerializer.SerializeToUtf8Bytes(selected),null,DataProtectionScope.CurrentUser));
   browser?.Dispose();content.Controls.Clear();browser=new WebView2{Dock=DockStyle.Fill};content.Controls.Add(browser);
   var profile=Path.Combine(home,smokeFile==null?"browser":"smoke-browser");
   var environment=await CoreWebView2Environment.CreateAsync(null,profile);
   await browser.EnsureCoreWebView2Async(environment);
   var web=browser.CoreWebView2;
   web.Settings.AreDevToolsEnabled=false;web.Settings.AreHostObjectsAllowed=false;web.Settings.IsPasswordAutosaveEnabled=false;web.Settings.IsGeneralAutofillEnabled=false;web.Settings.AreDefaultContextMenusEnabled=true;
   bool SameOrigin(string value) => Uri.TryCreate(value,UriKind.Absolute,out var target)&&target.Scheme==uri.Scheme&&target.Host==uri.Host&&target.Port==uri.Port;
   web.ServerCertificateErrorDetected+=(_,e)=>{
    try{using var cert=X509Certificate2.CreateFromPem(e.ServerCertificate.ToPemEncoding());e.Action=SameOrigin(e.RequestUri)&&selected.Matches(cert)?CoreWebView2ServerCertificateErrorAction.AlwaysAllow:CoreWebView2ServerCertificateErrorAction.Cancel;}catch{e.Action=CoreWebView2ServerCertificateErrorAction.Cancel;}
   };
   web.AddWebResourceRequestedFilter("*",CoreWebView2WebResourceContext.All,CoreWebView2WebResourceRequestSourceKinds.All);
   web.WebResourceRequested+=(_,e)=>{if(SameOrigin(e.Request.Uri))e.Request.Headers.SetHeader("Authorization","Bearer "+selected.AccessKey);};
   web.NavigationStarting+=(_,e)=>{if(!SameOrigin(e.Uri)){e.Cancel=true;status.Text="Navegação externa bloqueada nesta janela. Use os links de referência.";}};
   web.NewWindowRequested+=(_,e)=>{e.Handled=true;if(e.IsUserInitiated&&Uri.TryCreate(e.Uri,UriKind.Absolute,out var external)&&external.Scheme=="https")Process.Start(new ProcessStartInfo(external.AbsoluteUri){UseShellExecute=true});};
   web.DownloadStarting+=(_,e)=>{e.Cancel=true;status.Text="Downloads devem ser feitos no servidor.";};
   web.DOMContentLoaded+=async (_,_)=>{
    await web.ExecuteScriptAsync("(()=>{const f=document.getElementById('connect-form')||document.getElementById('login-form');const t=document.getElementById('local-token')||document.getElementById('token');if(f&&t){t.value='dispositivo-pareado';f.requestSubmit();}const logout=document.getElementById('logout');if(logout)logout.hidden=true;})()");
   };
   web.NavigationCompleted+=(_,e)=>{status.Text=e.IsSuccess ? "Conectado a "+selected.Server+" · "+selected.Name : "Falha ao carregar. Clique em Reconectar.";};
   web.Navigate(selected.Server);
   if(reportFile!=null) {
    bool logged=false;
    for(int attempt=0;attempt<80;attempt++){await Task.Delay(250);if(await web.ExecuteScriptAsync("Boolean(document.getElementById('studio') && !document.getElementById('studio').hidden)")=="true"){logged=true;break;}}
    if(logged){using var file=File.Create(Path.ChangeExtension(reportFile,"png"));await web.CapturePreviewAsync(CoreWebView2CapturePreviewImageFormat.Png,file);}
    await File.WriteAllTextAsync(reportFile,JsonSerializer.Serialize(new{passed=logged,pinnedTls=true,authenticated=true,desktopLogin=logged}));Environment.ExitCode=logged?0:1;Close();
   }
  } catch(Exception e){await Failure(e);} finally{connecting=false;if(!IsDisposed)import.Enabled=reconnect.Enabled=forget.Enabled=true;}
 }
}
