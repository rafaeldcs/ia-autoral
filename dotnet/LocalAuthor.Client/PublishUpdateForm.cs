using System.Diagnostics;
using System.Net.Http.Json;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using LocalAuthor.Connectivity;

namespace LocalAuthor.Client;

static class RemotePublication {
 public static async Task<Permission?> Status(Connection connection, CancellationToken cancel) {
  using var client=ClientUpdates.CreateClient(connection);
  using var deadline=CancellationTokenSource.CreateLinkedTokenSource(cancel);deadline.CancelAfter(TimeSpan.FromSeconds(5));
  using var response=await client.GetAsync("/api/device",deadline.Token);
  if(!response.IsSuccessStatusCode)return null;
  var permission=await response.Content.ReadFromJsonAsync<Permission>(deadline.Token);
  return permission;
 }
 public record Permission(bool CanPublishUpdates,bool PublicationPasswordConfigured=false,bool PublicationPasswordRequired=false);
 public static async Task<bool> IsAllowed(Connection connection,CancellationToken cancel)=>(await Status(connection,cancel))?.CanPublishUpdates==true;
 public static async Task SetPassword(Connection connection,string password,CancellationToken cancel){
  using var client=ClientUpdates.CreateClient(connection);
  // JsonContent streams with no Content-Length. The gateway requires a bounded,
  // declared payload; buffered UTF-8 supplies the exact byte length, including accents.
  using var content=new StringContent(JsonSerializer.Serialize(new{password}),Encoding.UTF8,"application/json");
  using var response=await client.PostAsync("/api/publication-password",content,cancel);
  if(!response.IsSuccessStatusCode)throw new InvalidOperationException((int)response.StatusCode==409?"A senha já foi cadastrada neste servidor. Use a senha existente ao publicar.":"Não foi possível cadastrar. Use de 12 a 256 caracteres e confira a conexão.");
  var permission=await Status(connection,cancel);
  if(permission?.PublicationPasswordConfigured!=true)throw new InvalidOperationException("O cadastro foi enviado, mas não foi possível confirmar. Confira a conexão antes de tentar novamente.");
 }
 public static async Task<ClientRelease> Inspect(string path, CancellationToken cancel) {
  var info=FileVersionInfo.GetVersionInfo(path);
  if(info.ProductName!="LocalAuthor.Client"||info.OriginalFilename!="LocalAuthor.Client.dll")
   throw new InvalidDataException("Selecione o executável do cliente LocalAuthor, não o instalador.");
  using var file=new FileStream(path,FileMode.Open,FileAccess.Read,FileShare.Read);
  if(file.Length>ClientRelease.MaxSize)throw new InvalidDataException("O arquivo excede 300 MB.");
  var release=new ClientRelease(info.FileVersion!,Convert.ToHexString(await SHA256.HashDataAsync(file,cancel)),file.Length);
  release.Validate();return release;
 }
 public static async Task Publish(Connection connection,string path,ClientRelease release,string password,CancellationToken cancel) {
  using var file=new FileStream(path,FileMode.Open,FileAccess.Read,FileShare.Read);
  await release.VerifyAsync(path,cancel);
  using var client=ClientUpdates.CreateClient(connection);
  using var request=new HttpRequestMessage(HttpMethod.Post,"/api/client-update/publish");
  request.Headers.Add("X-Release-Version",release.Version);request.Headers.Add("X-Release-Sha256",release.Sha256);
  request.Headers.Add("X-Publication-Password",Convert.ToBase64String(System.Text.Encoding.UTF8.GetBytes(password)));
  request.Content=new StreamContent(file);request.Content.Headers.ContentType=new("application/octet-stream");
  using var response=await client.SendAsync(request,cancel);
  if(!response.IsSuccessStatusCode)throw new InvalidOperationException((int)response.StatusCode switch {
   401=>"A conexão deste dispositivo foi revogada.",
   403=>"Senha incorreta ou conexão revogada. A publicação não foi autorizada.",
   428=>"Cadastre a senha de publicação na primeira abertura do aplicativo.",
   429=>"Muitas tentativas. Aguarde um minuto antes de tentar novamente.",
   409=>"Essa versão é antiga ou já foi publicada com outro conteúdo. Aumente a versão e compile novamente.",
   400=>"O servidor recusou o pacote. Confira executável, versão e integridade.",
   _=>"O servidor não concluiu a publicação. Confira a conexão e tente novamente."
  });
 }
}

sealed class PublishUpdateForm : Form {
 readonly Connection connection;
 readonly Button choose=new(){Text="Escolher nova versão…",AutoSize=true};
 readonly Button publish=new(){Text="Publicar para os clientes",AutoSize=true,Enabled=false};
 readonly CheckBox reviewed=new(){Text="Compilei, testei e revisei esta versão para distribuição.",AutoSize=true};
 readonly TextBox password=new(){UseSystemPasswordChar=true,MaxLength=256,Width=520};
 readonly Label details=new(){AutoSize=true,MaximumSize=new Size(530,0),Text="Selecione o arquivo LocalAuthor.Client.exe de uma versão compilada e testada. O servidor distribuirá essa versão aos clientes conectados.\n\nO instalador não deve ser selecionado aqui."};
 readonly CancellationTokenSource cancel=new();
 string? file;ClientRelease? release;bool sending;
 public PublishUpdateForm(Connection selected) {
  connection=selected;Text="Publicar atualização";ClientSize=new Size(600,500);Font=new Font("Segoe UI",10);StartPosition=FormStartPosition.CenterParent;
  var panel=new FlowLayoutPanel{Dock=DockStyle.Fill,Padding=new Padding(20),FlowDirection=FlowDirection.TopDown,WrapContents=false,AutoScroll=true};
  foreach(Control control in new Control[]{details,choose,new Label{Text="Senha de publicação",AutoSize=true},password,reviewed,publish}){control.Margin=new Padding(0,0,0,16);panel.Controls.Add(control);}Controls.Add(panel);
  reviewed.CheckedChanged+=(_,_)=>publish.Enabled=release!=null&&reviewed.Checked&&password.Text.Length>=12&&!sending;
  password.TextChanged+=(_,_)=>publish.Enabled=release!=null&&reviewed.Checked&&password.Text.Length>=12&&!sending;
  FormClosing+=(_,e)=>{if(sending){e.Cancel=true;details.Text="Aguarde o envio terminar para fechar esta janela.";}};
  FormClosed+=(_,_)=>{cancel.Cancel();cancel.Dispose();};
  choose.Click+=async(_,_)=>{
   using var picker=new OpenFileDialog{Title="Selecione o cliente compilado",Filter="Cliente Windows|*.exe",CheckFileExists=true};if(picker.ShowDialog(this)!=DialogResult.OK)return;
   choose.Enabled=false;publish.Enabled=false;reviewed.Checked=false;release=null;
   try{file=picker.FileName;release=await RemotePublication.Inspect(file,cancel.Token);details.Text=$"Arquivo: {Path.GetFileName(file)}\nVersão: {release.Version}\nTamanho: {release.Size/1048576.0:F1} MB\nSHA-256: {release.Sha256}\n\nApós publicar, os clientes buscarão a atualização automaticamente.";}
   catch(Exception e){details.Text=e.Message;}finally{choose.Enabled=true;}
  };
  publish.Click+=async(_,_)=>{
   if(release==null||file==null||!reviewed.Checked)return;
   sending=true;choose.Enabled=publish.Enabled=reviewed.Enabled=false;details.Text="Enviando e validando no servidor… Aguarde a confirmação.";
   try{await RemotePublication.Publish(connection,file,release,password.Text,cancel.Token);details.Text=$"Versão {release.Version} publicada. Os clientes verificarão em até cinco minutos enquanto estiverem conectados e com o aplicativo aberto.";release=null;}
   catch(Exception e){details.Text=e is HttpRequestException or TaskCanceledException?"Conexão interrompida. O resultado pode ser conferido repetindo a publicação do mesmo arquivo.":e.Message;}
   finally{password.Clear();sending=false;choose.Enabled=reviewed.Enabled=true;publish.Enabled=false;}
  };
 }
}

sealed class PublicationPasswordForm : Form {
 readonly TextBox password=new(){Width=460,UseSystemPasswordChar=true,MaxLength=256};
 readonly TextBox confirm=new(){Width=460,UseSystemPasswordChar=true,MaxLength=256};
 readonly Label message=new(){Text="Esta senha autoriza publicar atualizações para os computadores conectados. Ela não é necessária para conversar com a IA. Use de 12 a 256 caracteres.",AutoSize=true,MaximumSize=new Size(460,0)};
 readonly Button save=new(){Text="Salvar senha",AutoSize=true};
 bool saving,saved;
 public PublicationPasswordForm(Connection connection){
  Text="Primeiro acesso — senha de publicação";ClientSize=new Size(540,430);Font=new Font("Segoe UI",10);StartPosition=FormStartPosition.CenterParent;AcceptButton=save;
  var panel=new FlowLayoutPanel{Dock=DockStyle.Fill,Padding=new Padding(24),FlowDirection=FlowDirection.TopDown,WrapContents=false,AutoScroll=true};
  var passwordLabel=new Label{Text="Nova senha",AutoSize=true};var confirmLabel=new Label{Text="Confirmar senha",AutoSize=true};
  var later=new Button{Text="Agora não — abrir a IA",AutoSize=true};
  foreach(Control control in new Control[]{message,passwordLabel,password,confirmLabel,confirm,save,later}){control.Margin=new Padding(0,0,0,10);panel.Controls.Add(control);}Controls.Add(panel);
  later.Click+=(_,_)=>{if(!saving){DialogResult=DialogResult.Cancel;Close();}};
  FormClosing+=(_,e)=>e.Cancel=saving;
  FormClosed+=(_,_)=>{password.Clear();confirm.Clear();};
  save.Click+=async(_,_)=>{
   if(saved){DialogResult=DialogResult.OK;Close();return;}
   if(password.Text.Length<12||string.IsNullOrWhiteSpace(password.Text)){message.Text="A senha precisa ter de 12 a 256 caracteres e não pode conter apenas espaços.";password.Focus();return;}
   if(password.Text!=confirm.Text){message.Text="As senhas estão diferentes. Corrija a confirmação; os campos foram mantidos.";confirm.Focus();return;}
   saving=true;save.Enabled=later.Enabled=password.Enabled=confirm.Enabled=false;save.Text="Salvando…";message.Text="Salvando no servidor e verificando a confirmação…";
   try{
    using var timeout=new CancellationTokenSource(TimeSpan.FromSeconds(15));await RemotePublication.SetPassword(connection,password.Text,timeout.Token);
    saved=true;password.Clear();confirm.Clear();password.Visible=confirm.Visible=passwordLabel.Visible=confirmLabel.Visible=later.Visible=false;
    message.Text="Senha de publicação salva e confirmada no servidor.\n\nUse essa senha quando publicar uma atualização. Agora você pode abrir sua IA.";
    message.ForeColor=Color.FromArgb(27,119,80);save.Text="Abrir minha IA";
   }
   catch(Exception e){message.Text=e is HttpRequestException or TaskCanceledException?"Não foi possível confirmar o cadastro no servidor. Seus campos foram mantidos; confira a conexão e tente novamente.":e.Message;}
   finally{saving=false;save.Enabled=later.Enabled=password.Enabled=confirm.Enabled=true;if(!saved)save.Text="Salvar senha";}
  };
 }
}
