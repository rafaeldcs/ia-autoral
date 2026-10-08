using LocalAuthor.Connectivity;
using System.Diagnostics;
using System.Net;
using System.Net.NetworkInformation;
using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;
using System.Text.Json;
using Microsoft.Web.WebView2.Core;
using Microsoft.Web.WebView2.WinForms;

namespace LocalAuthor.Client;
static class Program {
 [STAThread] static void Main(string[] args) {
  if(args.Length==4&&args[0]=="--local-startup-smoke"){
   try{var local=new LocalServerConnection(args[1],args[2]);var value=local.PrepareAsync(_=>{},CancellationToken.None).GetAwaiter().GetResult();File.WriteAllText(args[3],JsonSerializer.Serialize(new{passed=value!=null,local=local.UsingLocalServer,server=value?.Server}));if(value==null)Environment.ExitCode=1;}catch(Exception e){File.WriteAllText(args[3],JsonSerializer.Serialize(new{passed=false,error=e.GetType().Name}));Environment.ExitCode=1;}return;
  }
  if(args.Length==3&&args[0]=="--password-setup-smoke"){
   Console.InputEncoding=System.Text.Encoding.UTF8;
   try{var connection=Connection.Import(args[1]);RemotePublication.SetPassword(connection,Console.ReadLine()??"",CancellationToken.None).GetAwaiter().GetResult();var status=RemotePublication.Status(connection,CancellationToken.None).GetAwaiter().GetResult();File.WriteAllText(args[2],JsonSerializer.Serialize(new{passed=status?.PublicationPasswordConfigured==true}));}catch(Exception e){File.WriteAllText(args[2],JsonSerializer.Serialize(new{passed=false,error=e.GetType().Name}));Environment.ExitCode=1;}return;
  }
  if(args.Length==2&&args[0]=="--startup-check"){
   try{File.WriteAllText(args[1],JsonSerializer.Serialize(WindowsStartup.CheckInIsolatedRegistry(Environment.ProcessPath!)));}catch(Exception e){File.WriteAllText(args[1],JsonSerializer.Serialize(new{passed=false,error=e.GetType().Name}));Environment.ExitCode=1;}return;
  }
  if(args.Length==4&&args[0]=="--publish-smoke"){
   try{var connection=Connection.Import(args[1]);var release=RemotePublication.Inspect(args[2],CancellationToken.None).GetAwaiter().GetResult();RemotePublication.Publish(connection,args[2],release,Console.ReadLine()??"",CancellationToken.None).GetAwaiter().GetResult();File.WriteAllText(args[3],"{\"passed\":true}");}catch(Exception e){File.WriteAllText(args[3],JsonSerializer.Serialize(new{passed=false,error=e.GetType().Name}));Environment.ExitCode=1;}return;
  }
  if(args.Length==2&&args[0]=="--apply-update"){Environment.ExitCode=UpdateInstaller.ApplyAsync(args[1]).GetAwaiter().GetResult();return;}
  if(args.Length==3&&args[0]=="--update-smoke"){
   try{RunUpdateSmoke(args[1],args[2]).GetAwaiter().GetResult();}catch(Exception e){File.WriteAllText(args[2],JsonSerializer.Serialize(new{passed=false,error=e.GetType().Name}));Environment.ExitCode=1;}return;
  }
  if(args.Length==0||args.SequenceEqual(new[]{"--startup"})||args.Contains("--updated")){
   try{WindowsStartup.EnsureInstalledDefault();}catch(Exception e) when(e is UnauthorizedAccessException or System.Security.SecurityException or IOException){ /* System policy must not prevent using the app. */ }
  }
  ApplicationConfiguration.Initialize();Application.Run(new ClientForm(args));
 }
 static async Task RunUpdateSmoke(string source,string report){
  var connection=await ServerLocator.ResolveAsync(Connection.Import(source),_=>{},CancellationToken.None);
  var release=await ClientUpdates.CheckAsync(connection,CancellationToken.None)??throw new InvalidDataException("Atualização ausente para teste.");
  var folder=await ClientUpdates.DownloadAsync(connection,release,CancellationToken.None);
  File.WriteAllText(Path.Combine(folder,"smoke.json"),JsonSerializer.Serialize(new[]{Path.GetFullPath(source),Path.GetFullPath(report)}));
  File.WriteAllText(report+".job",folder);
  await ClientUpdates.LaunchAsync(folder,release,CancellationToken.None);
 }
}
sealed class ClientForm : Form {
 readonly string home=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"LocalAuthorClient");
 readonly Label status=new(){AutoSize=true,Text="Preparando sua conexão…",Margin=new Padding(12)};
 readonly Button import=new(){Text="Ajuda de conexão",AutoSize=true,Height=36};
 readonly Button reconnect=new(){Text="Reconectar",AutoSize=true,Height=36};
 readonly Button forget=new(){Text="Esquecer conexão",AutoSize=true,Height=36};
 readonly Button publishUpdate=new(){Text="Publicar atualização…",AutoSize=true,Enabled=false};
 bool publishing;
 readonly Button postponeUpdate=new(){Text="Adiar atualização",AutoSize=true,Visible=false};
 readonly Label updateStatus=new(){AutoSize=true,Margin=new Padding(12)};
 readonly Panel content=new(){Dock=DockStyle.Fill};
 readonly FlowLayoutPanel notices=new(){Dock=DockStyle.Bottom,AutoSize=true,Padding=new Padding(8),Visible=false};
 readonly ContextMenuStrip settingsMenu=new();
 readonly ToolStripMenuItem connectionInfo=new(){Enabled=false};
 readonly ToolStripMenuItem versionInfo=new(){Enabled=false};
 WebView2? browser;Connection? connection;bool connecting;
 bool pageLoaded;
 bool recovering;
 readonly System.Windows.Forms.Timer retryTimer=new(){Interval=15000};
 readonly System.Windows.Forms.Timer updateTimer=new(){Interval=300000};
 bool checkingUpdate,applyingUpdate;DateTime nextUpdate=DateTime.MinValue;
 bool automaticAttempt;
 readonly LocalServerConnection localServer;
 bool loadingSaved;
 readonly CancellationTokenSource shutdown=new();
 readonly string? smokeFile;readonly string? reportFile;
 readonly string? automaticTestReport;
 public ClientForm(string[] args) {
  Text="LocalAuthor — IA da sua rede";Width=1280;Height=880;MinimumSize=new Size(700,550);StartPosition=FormStartPosition.CenterScreen;
  Font=new Font("Segoe UI",10);BackColor=Color.White;
  // A healthy connection needs no native header. Administration is opened from Tools.
  settingsMenu.Items.AddRange([connectionInfo,versionInfo,new ToolStripSeparator()]);
  foreach(var action in new[]{import,reconnect,forget,publishUpdate}){
   var item=new ToolStripMenuItem(action.Text);item.Click+=(_,_)=>action.PerformClick();
   settingsMenu.Items.Add(item);action.TextChanged+=(_,_)=>item.Text=action.Text;
   action.EnabledChanged+=(_,_)=>item.Enabled=action.Enabled;action.VisibleChanged+=(_,_)=>item.Visible=action.Visible;
  }
  settingsMenu.Opening+=(_,_)=>{
   connectionInfo.Text=status.Text;versionInfo.Text="Cliente "+ClientUpdates.CurrentVersion+" · busca automática na rede local";
   for(int n=0;n<4;n++){var action=new[]{import,reconnect,forget,publishUpdate}[n];settingsMenu.Items[n+3].Enabled=action.Enabled;settingsMenu.Items[n+3].Visible=action.Visible;}
  };
  var waiting=new Label{Dock=DockStyle.Fill,Text=status.Text,TextAlign=ContentAlignment.MiddleCenter,Font=new Font("Segoe UI",16)};
  var configure=new Button{Dock=DockStyle.Bottom,Height=48,Text="Configurações de conexão"};configure.Click+=(_,_)=>ShowSettings();
  status.TextChanged+=(_,_)=>waiting.Text=status.Text;
  content.Controls.Add(waiting);content.Controls.Add(configure);
  notices.Controls.AddRange([updateStatus,postponeUpdate]);
  updateStatus.TextChanged+=(_,_)=>notices.Visible=!string.IsNullOrWhiteSpace(updateStatus.Text);
  Controls.Add(content);Controls.Add(notices);
  int i=Array.IndexOf(args,"--smoke");if(i>=0){smokeFile=args[i+1];reportFile=args[i+2];Opacity=0;ShowInTaskbar=false;}
  int savedIndex=Array.IndexOf(args,"--smoke-saved");if(savedIndex>=0){home=Path.GetFullPath(args[savedIndex+1]);reportFile=args[savedIndex+2];Opacity=0;ShowInTaskbar=false;}
  int autoIndex=Array.IndexOf(args,"--auto-update-smoke");if(autoIndex>=0){smokeFile=Path.GetFullPath(args[autoIndex+1]);automaticTestReport=Path.GetFullPath(args[autoIndex+2]);home=Path.Combine(Path.GetDirectoryName(automaticTestReport)!,"isolated-client-data");Opacity=0;ShowInTaskbar=false;}
  int localIndex=Array.IndexOf(args,"--smoke-local-server");
  if(localIndex>=0){home=Path.GetFullPath(args[localIndex+2]);reportFile=args[localIndex+3];Opacity=0;ShowInTaskbar=false;}
  // Existing isolated smoke modes must never enroll into the real user's server.
  var localData=localIndex>=0?Path.GetFullPath(args[localIndex+1]):reportFile!=null||automaticTestReport!=null?home:Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
  localServer=new LocalServerConnection(localData,home);
  Directory.CreateDirectory(home);
  NetworkChange.NetworkAddressChanged+=NetworkChanged;
  retryTimer.Tick+=async(_,_)=>await RecoverConnection();
  updateTimer.Tick+=async(_,_)=>await CheckForUpdates();
  publishUpdate.Click+=async(_,_)=>{if(connection==null||connecting||checkingUpdate)return;publishing=true;try{if(!await EnsurePublicationPassword())return;using var form=new PublishUpdateForm(connection);form.ShowDialog(this);}finally{publishing=false;}};
  postponeUpdate.Click+=(_,_)=>{nextUpdate=DateTime.UtcNow.AddMinutes(30);updateStatus.Text="Atualização adiada por 30 minutos.";};
  if(reportFile==null)retryTimer.Start();
  if(reportFile==null)updateTimer.Start();
  FormClosed+=(_,_)=>{NetworkChange.NetworkAddressChanged-=NetworkChanged;retryTimer.Stop();retryTimer.Dispose();updateTimer.Stop();updateTimer.Dispose();shutdown.Cancel();browser?.Dispose();settingsMenu.Dispose();};
  import.Click+=async (_,_)=>{if(localServer.UsingLocalServer||localServer.IsConfigured&&connection==null){await LoadSaved();return;}MessageBox.Show(this,"Instale a cópia privada do aplicativo vinculada ao seu servidor. Ela configura a conexão automaticamente, sem arquivo ou IP manual.\n\nSe já estava conectado, mantenha o servidor ligado e os dois computadores na mesma rede. O aplicativo tenta reencontrá-lo automaticamente.","Conexão automática",MessageBoxButtons.OK,MessageBoxIcon.Information);};
  reconnect.Click+=async (_,_)=>{if(connection!=null&&!localServer.UsingLocalServer)await Connect(connection);else await LoadSaved();};
  forget.Click+=(_,_)=>{if(MessageBox.Show(this,"Remover a conexão salva neste computador? Os projetos permanecem no servidor.","Esquecer conexão",MessageBoxButtons.YesNo,MessageBoxIcon.Question)!=DialogResult.Yes)return;File.Delete(Path.Combine(home,"connection.bin"));connection=null;browser?.Dispose();browser=null;status.Text="Conexão removida. Instale a cópia vinculada ao servidor desejado.";};
  Shown+=async (_,_)=>{
   int updated=Array.IndexOf(args,"--updated");if(updated>=0)UpdateInstaller.Acknowledge(args[updated+1]);
   automaticAttempt=true;try{if(smokeFile!=null)await ConnectFile(smokeFile);else await LoadSaved();}finally{automaticAttempt=false;}
   if(reportFile==null){
    if(automaticTestReport==null)await EnsurePublicationPassword();
    for(int attempt=0;attempt<40&&!IsDisposed;attempt++){if(await SafeToRestart())break;await Task.Delay(250);}
    if(automaticTestReport!=null&&args.Contains("--draft"))await browser!.CoreWebView2.ExecuteScriptAsync("document.getElementById('message-input').value='rascunho de teste';");
    if(automaticTestReport!=null&&args.Contains("--appearance"))await browser!.CoreWebView2.ExecuteScriptAsync("(()=>{const appearance=document.querySelector('[data-appearance]');appearance.value='dark';appearance.dispatchEvent(new Event('input',{bubbles:true}));appearance.dispatchEvent(new Event('change',{bubbles:true}));})()");
    if(!IsDisposed)await CheckForUpdates();
    if(automaticTestReport!=null&&args.Contains("--draft")){
     var preserved=await browser!.CoreWebView2.ExecuteScriptAsync("document.getElementById('message-input').value==='rascunho de teste'")=="true";
     File.WriteAllText(automaticTestReport,JsonSerializer.Serialize(new{passed=preserved&&!File.Exists(automaticTestReport+".job"),draftPreserved=preserved}));Close();
    }
   }
  };
 }
 void ShowSettings(){if(!IsDisposed)settingsMenu.Show(this,new Point(Math.Max(0,ClientSize.Width-settingsMenu.Width-16),Math.Max(0,ClientSize.Height-settingsMenu.Height-16)));}
 protected override bool ProcessCmdKey(ref Message message,Keys keys){if(keys==(Keys.Control|Keys.Oemcomma)){ShowSettings();return true;}return base.ProcessCmdKey(ref message,keys);}
 async Task RecoverConnection(){
  if(recovering||connecting||loadingSaved||applyingUpdate||publishing||IsDisposed)return;
  recovering=true;
  try{
  try{if(connection!=null&&browser!=null&&pageLoaded&&await ServerLocator.ProbeAsync(connection,shutdown.Token)){status.Text="Conectado a "+connection.Server+" · "+connection.Name;return;}}
  catch(System.Security.Authentication.AuthenticationException){retryTimer.Stop();status.Text="Acesso revogado. Solicite uma conexão atualizada.";updateStatus.Text=status.Text;return;}
  catch(OperationCanceledException){return;}
  automaticAttempt=true;
  try{if(connection==null||localServer.UsingLocalServer)await LoadSaved();else await Connect(connection);}
  finally{automaticAttempt=false;}
  if(pageLoaded&&!IsDisposed)await CheckForUpdates();
  }finally{recovering=false;}
 }
 async Task<bool> EnsurePublicationPassword(){
  if(connection==null||reportFile!=null||automaticTestReport!=null)return false;
  try{
   var permission=await RemotePublication.Status(connection,shutdown.Token);
   if(permission==null)return false;
   if(permission.PublicationPasswordConfigured)return true;
   if(!permission.PublicationPasswordRequired){status.Text="Atualize o servidor para cadastrar a senha de publicação.";return false;}
   var wasPublishing=publishing;publishing=true;
   try{using var form=new PublicationPasswordForm(connection);return form.ShowDialog(this)==DialogResult.OK;}finally{publishing=wasPublishing;}
  }catch{status.Text="Não foi possível consultar a senha de publicação no servidor.";return false;}
 }
 async Task<bool> SafeToRestart(){
  if(browser?.CoreWebView2==null||connecting)return false;
  // Only restart from an idle chat. Other screens may contain unsaved forms.
  return await browser.CoreWebView2.ExecuteScriptAsync("Boolean(document.getElementById('studio')&&!document.getElementById('studio').hidden&&typeof state!=='undefined'&&!state.busy&&!document.getElementById('message-input').value&&!window.__localAuthorUpdateDirty)")=="true";
 }
 async Task CheckForUpdates(){
  if(connection==null||checkingUpdate||connecting||publishing||reportFile!=null||DateTime.UtcNow<nextUpdate)return;
  checkingUpdate=true;
  try{
   var selected=connection;var release=await ClientUpdates.CheckAsync(selected,shutdown.Token);if(release==null){updateStatus.Text="";return;}
   updateStatus.Text="Nova versão disponível. Aguardando o chat ficar livre…";
   if(!await SafeToRestart())return;
   updateStatus.Text="Baixando atualização… Você pode continuar usando o chat.";
   var folder=await ClientUpdates.DownloadAsync(selected,release,shutdown.Token);
   if(automaticTestReport!=null){File.WriteAllText(Path.Combine(folder,"smoke.json"),JsonSerializer.Serialize(new[]{smokeFile!,automaticTestReport}));File.WriteAllText(automaticTestReport+".job",folder);}
   postponeUpdate.Visible=true;
   for(int remaining=15;remaining>0;remaining--){
    if(connection!=selected||DateTime.UtcNow<nextUpdate||!await SafeToRestart()){File.Delete(Path.Combine(folder,"download.exe"));updateStatus.Text="Atualização adiada para preservar seu trabalho.";return;}
    updateStatus.Text=$"Atualização pronta. O aplicativo reabrirá em {remaining}s.";await Task.Delay(1000,shutdown.Token);
   }
   if(connection!=selected||DateTime.UtcNow<nextUpdate||!await SafeToRestart()){File.Delete(Path.Combine(folder,"download.exe"));return;}
   applyingUpdate=true;import.Enabled=reconnect.Enabled=forget.Enabled=false;if(browser!=null)browser.Enabled=false;
   await ClientUpdates.LaunchAsync(folder,release,shutdown.Token);Close();
  }catch(OperationCanceledException){}catch(Exception){updateStatus.Text="Não foi possível atualizar agora. Nova tentativa automática em 5 minutos.";}
  finally{checkingUpdate=false;applyingUpdate=false;if(!IsDisposed){postponeUpdate.Visible=false;import.Enabled=reconnect.Enabled=forget.Enabled=true;if(browser!=null)browser.Enabled=true;}}
 }
 void NetworkChanged(object? sender,EventArgs args){if(IsDisposed||!IsHandleCreated)return;try{BeginInvoke(new Action(async()=>{if(!IsDisposed){status.Text="Rede alterada. Vou procurar seu servidor automaticamente…";await RecoverConnection();}}));}catch(InvalidOperationException){}}
 async Task LoadSaved(){
  if(loadingSaved)return;loadingSaved=true;import.Enabled=reconnect.Enabled=false;
  try{
   var selected=await localServer.PrepareAsync(text=>status.Text=text,shutdown.Token);
   import.Text=localServer.UsingLocalServer?"Abrir IA deste computador":"Ajuda de conexão";forget.Visible=!localServer.UsingLocalServer;
   if(selected!=null)await Connect(selected);
   else if(reportFile!=null)await Failure(new FileNotFoundException("Conexão salva ausente."));
   else status.Text="Servidor não configurado neste computador. Instale o aplicativo vinculado ao seu servidor.";
  }catch(Exception e){await Failure(e);}finally{loadingSaved=false;if(!IsDisposed)import.Enabled=reconnect.Enabled=true;}
 }
 async Task ConnectFile(string path){try{await Connect(Connection.Import(path));}catch(Exception e){await Failure(e);}}
 async Task Failure(Exception error) {
  status.Text=localServer.UsingLocalServer?"A IA deste computador ainda não respondeu. Nova tentativa automática; diagnóstico em LocalAuthor/lan.":"Não foi possível conectar. Confira se o servidor está ligado e na mesma rede.";
  if(error is System.Security.Authentication.AuthenticationException){retryTimer.Stop();status.Text="Acesso revogado. Solicite uma conexão atualizada.";}
  if(browser!=null)updateStatus.Text=status.Text;
  if(reportFile!=null){await File.WriteAllTextAsync(reportFile,JsonSerializer.Serialize(new{passed=false,error=error.GetType().Name}));Environment.ExitCode=1;Close();}
  else if(!automaticAttempt && error is not HttpRequestException && error is not OperationCanceledException) MessageBox.Show(this,error is HttpRequestException ? "Conexão recusada, certificado diferente ou acesso revogado. Confira o servidor e importe uma conexão atualizada." : error.Message,"LocalAuthor",MessageBoxButtons.OK,MessageBoxIcon.Information);
 }
 async Task Connect(Connection selected) {
  if(connecting)return;connecting=true;import.Enabled=reconnect.Enabled=forget.Enabled=false;
  try {
   if(browser!=null)browser.Enabled=false;
   string? draft=null;
   if(browser?.CoreWebView2!=null&&connection?.CertificateSha256==selected.CertificateSha256){
    draft=await browser.CoreWebView2.ExecuteScriptAsync("(()=>{const input=document.getElementById('message-input');return input&&input.value&&typeof state!=='undefined'?{message:input.value,project:state.project?.id,conversation:state.conversation?.id,format:document.getElementById('input-format').value,mode:document.getElementById('response-mode').value}:null;})()");
    if(draft=="null")draft=null;
   }
   connection=selected;
   publishUpdate.Enabled=false;
   status.Text="Verificando servidor e identidade…";
   selected=await ServerLocator.ResolveAsync(selected,text=>status.Text=text,shutdown.Token);
   var uri=selected.Validate();
   connection=selected;
   try{publishUpdate.Enabled=await RemotePublication.IsAllowed(selected,shutdown.Token);}catch{publishUpdate.Enabled=false;}
   if(reportFile==null) LocalServerConnection.Save(home,selected);
   pageLoaded=false;browser?.Dispose();content.Controls.Clear();browser=new WebView2{Dock=DockStyle.Fill};content.Controls.Add(browser);
   var profile=Path.Combine(home,smokeFile==null?"browser":"smoke-browser");
   var environment=await CoreWebView2Environment.CreateAsync(null,profile);
   await browser.EnsureCoreWebView2Async(environment);
   var web=browser.CoreWebView2;
   web.WebMessageReceived+=(_,e)=>{try{if(DesktopShell.Accepts(e.Source,uri,e.TryGetWebMessageAsString()))ShowSettings();}catch(Exception error) when(error is ArgumentException or InvalidOperationException or System.Runtime.InteropServices.COMException){ /* Ignore non-string messages. */ }};
   await web.AddScriptToExecuteOnDocumentCreatedAsync("window.__localAuthorUpdateDirty=false;document.addEventListener('input',e=>{if(!e.target.matches('#message-input,#local-token,#response-mode,#input-format,[data-appearance]'))window.__localAuthorUpdateDirty=true;},true);");
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
    await web.ExecuteScriptAsync(DesktopShell.MountScript);
    await web.ExecuteScriptAsync("(()=>{const f=document.getElementById('connect-form')||document.getElementById('login-form');const t=document.getElementById('local-token')||document.getElementById('token');if(f&&t){t.value='dispositivo-pareado';f.requestSubmit();}const logout=document.getElementById('logout');if(logout)logout.hidden=true;})()");
    if(draft!=null){
     // Keep the original project and conversation when restoring an unsent draft.
     var restore="(async()=>{const draft="+draft+";for(let i=0;i<80;i++){if(typeof state!=='undefined'&&state.project){const project=state.projects.find(p=>p.id===draft.project);if(!project)return;await selectProject(project);if(draft.conversation){try{state.conversation=await api('/api/conversation?project_id='+project.id+'&id='+draft.conversation);renderMessages();await renderConversations();}catch{}}document.getElementById('message-input').value=draft.message;document.getElementById('input-format').value=draft.format;document.getElementById('input-format').dispatchEvent(new Event('change'));document.getElementById('response-mode').value=draft.mode;modeNotice();updateInputCount();return;}await new Promise(r=>setTimeout(r,100));}})()";
     await web.ExecuteScriptAsync(restore);
    }
   };
   web.NavigationCompleted+=(_,e)=>{pageLoaded=e.IsSuccess;status.Text=e.IsSuccess ? "Conectado a "+selected.Server+" · "+selected.Name : "Falha ao carregar. Vou tentar novamente automaticamente.";};
   web.Navigate(selected.Server);
   if(reportFile!=null) {
    bool logged=false;
    for(int attempt=0;attempt<80;attempt++){await Task.Delay(250);if(await web.ExecuteScriptAsync("Boolean(document.getElementById('studio') && !document.getElementById('studio').hidden)")=="true"){logged=true;break;}}
    if(logged){using var file=File.Create(Path.ChangeExtension(reportFile,"png"));await web.CapturePreviewAsync(CoreWebView2CapturePreviewImageFormat.Png,file);}
    var shell=await web.ExecuteScriptAsync("Boolean(document.querySelector('#tools-dialog #desktop-settings'))")=="true";
    var noHeader=!Controls.Cast<Control>().Any(c=>c.Dock==DockStyle.Top);
    var trustedOnly=DesktopShell.Accepts(selected.Server,uri,"desktop-settings")&&!DesktopShell.Accepts("https://example.com",uri,"desktop-settings")&&!DesktopShell.Accepts(selected.Server,uri,"publish")&&!DesktopShell.Accepts(selected.Server,uri,"forget");
    await web.ExecuteScriptAsync("window.chrome.webview.postMessage({unexpected:true});window.chrome.webview.postMessage('publish');");await Task.Delay(150);
    var ignored=!settingsMenu.Visible;
    await web.ExecuteScriptAsync("document.getElementById('desktop-settings').click();");await Task.Delay(150);
    var menuOpened=settingsMenu.Visible;settingsMenu.Close();
    await File.WriteAllTextAsync(reportFile,JsonSerializer.Serialize(new{passed=logged&&shell&&noHeader&&trustedOnly&&ignored&&menuOpened,pinnedTls=true,authenticated=true,desktopLogin=logged,canPublishUpdates=publishUpdate.Enabled,desktopSettingsInTools=shell,nativeHeaderAbsent=noHeader,bridgeRestricted=trustedOnly,bridgeIgnoresInvalidMessages=ignored,desktopSettingsMenuOpened=menuOpened}));Environment.ExitCode=logged&&shell&&noHeader&&trustedOnly&&ignored&&menuOpened?0:1;Close();
   }
  } catch(Exception e){await Failure(e);} finally{connecting=false;if(!IsDisposed){import.Enabled=reconnect.Enabled=forget.Enabled=true;if(browser!=null)browser.Enabled=true;}}
 }
}
