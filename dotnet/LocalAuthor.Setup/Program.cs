using System.Diagnostics;
using System.IO.Compression;
using System.Reflection;
using System.Security.Cryptography;
using System.Text.Json;
using Microsoft.Win32;

namespace LocalAuthor.Setup;
static class Program {
 [STAThread] static void Main(string[] args) {
  ApplicationConfiguration.Initialize();
  if(args.Length==2&&args[0]=="--test-install") {
   try {var root=Path.Combine(Path.GetTempPath(),"LocalAuthor-setup-"+Guid.NewGuid().ToString("N"));var count=Installer.Extract(root);File.WriteAllText(args[1],JsonSerializer.Serialize(new{passed=true,files=count,path=root}));}
   catch(Exception e){File.WriteAllText(args[1],JsonSerializer.Serialize(new{passed=false,error=e.GetType().Name}));Environment.ExitCode=1;}return;
  }
  Application.Run(new SetupForm());
 }
}
static class Installer {
 public static readonly string Destination=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"Programs","LocalAuthorClient");
 public static int Extract(string root) {
  root=Path.GetFullPath(root);Directory.CreateDirectory(root);
  if((File.GetAttributes(root)&FileAttributes.ReparsePoint)!=0)throw new IOException("A pasta não pode ser um link.");
  using var stream=Assembly.GetExecutingAssembly().GetManifestResourceStream("payload.zip")!;
  using var zip=new ZipArchive(stream,ZipArchiveMode.Read);
  var manifestEntry=zip.GetEntry("payload-manifest.json") ?? throw new InvalidDataException("Manifesto ausente.");
  using var reader=new StreamReader(manifestEntry.Open());var manifest=JsonSerializer.Deserialize<Dictionary<string,string>>(reader.ReadToEnd())!;
  foreach(var (name,hash) in manifest) {
   if(Path.GetFileName(name)!=name||name.Contains(':')||name is "." or "..")throw new InvalidDataException("Caminho inválido no pacote.");
   var entry=zip.GetEntry(name) ?? throw new InvalidDataException("Arquivo ausente.");
   using var input=entry.Open();using var memory=new MemoryStream();input.CopyTo(memory);var bytes=memory.ToArray();
   if(Convert.ToHexString(SHA256.HashData(bytes))!=hash)throw new InvalidDataException("Integridade do pacote inválida.");
   var path=Path.Combine(root,name);
   if(File.Exists(path)&&(File.GetAttributes(path)&FileAttributes.ReparsePoint)!=0)throw new IOException("Destino não pode ser um link.");
   var pending=path+"."+Guid.NewGuid().ToString("N")+".installing";
   using(var output=new FileStream(pending,FileMode.CreateNew,FileAccess.Write,FileShare.None))output.Write(bytes);
   File.Move(pending,path,true);
  }
  File.WriteAllText(Path.Combine(root,"payload-manifest.json"),JsonSerializer.Serialize(manifest));return manifest.Count;
 }
 public static bool HasWebView() => new[]{Environment.GetFolderPath(Environment.SpecialFolder.ProgramFilesX86),Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles),Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData)}.Any(root=>{
  var path=Path.Combine(root,"Microsoft","EdgeWebView","Application");return Directory.Exists(path)&&Directory.EnumerateDirectories(path).Any(d=>File.Exists(Path.Combine(d,"msedgewebview2.exe")));
 });
 public static async Task EnsureWebView() {
  if(HasWebView())return;
  var file=Path.Combine(Path.GetTempPath(),"LocalAuthor-WebView-"+Guid.NewGuid().ToString("N")+".exe");
  try {
   using(var source=Assembly.GetExecutingAssembly().GetManifestResourceStream("webview.exe")!)using(var target=File.Create(file))await source.CopyToAsync(target);
   using var process=Process.Start(new ProcessStartInfo(file,"/silent /install"){UseShellExecute=false,CreateNoWindow=true,WindowStyle=ProcessWindowStyle.Hidden})!;
   await process.WaitForExitAsync();if(process.ExitCode!=0&&!HasWebView())throw new IOException("O WebView2 não pôde ser instalado. Consulte o guia incluído no pacote.");
  } finally {if(File.Exists(file))File.Delete(file);}
 }
 public static void Register() {
  var menu=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Programs),"LocalAuthor.lnk");
  dynamic shell=Activator.CreateInstance(Type.GetTypeFromProgID("WScript.Shell")!)!;
  dynamic shortcut=shell.CreateShortcut(menu);shortcut.TargetPath=Path.Combine(Destination,"LocalAuthor.Client.exe");shortcut.WorkingDirectory=Destination;shortcut.Description="Sua IA local pela rede";shortcut.Save();
  using var registry=Registry.CurrentUser.CreateSubKey(@"Software\Microsoft\Windows\CurrentVersion\Uninstall\LocalAuthorClient");
  registry.SetValue("DisplayName","LocalAuthor — Cliente de rede");registry.SetValue("DisplayVersion","0.2.0");registry.SetValue("Publisher","LocalAuthor experimental");registry.SetValue("InstallLocation",Destination);
  registry.SetValue("UninstallString","powershell.exe -NoProfile -ExecutionPolicy Bypass -File \""+Path.Combine(Destination,"Desinstalar.ps1")+"\"");registry.SetValue("NoModify",1);registry.SetValue("NoRepair",1);
 }
}
sealed class SetupForm : Form {
 bool installed;
 readonly Button install=new(){Text="Instalar LocalAuthor",AutoSize=true,Height=44};
 readonly Label message=new(){AutoSize=true,MaximumSize=new Size(500,0),Text="Instalação para este usuário do Windows.\n\nO aplicativo acessa a IA do seu servidor pela rede local.\n.NET está incluído. WebView2 será instalado se necessário, sem download.\n\nDepois, importe o arquivo de conexão criado no servidor.\nNenhuma chave de acesso está incluída neste instalador."};
 public SetupForm() {
  Text="Instalar LocalAuthor";ClientSize=new Size(560,350);StartPosition=FormStartPosition.CenterScreen;Font=new Font("Segoe UI",11);FormBorderStyle=FormBorderStyle.FixedDialog;MaximizeBox=false;
  var panel=new FlowLayoutPanel{Dock=DockStyle.Fill,FlowDirection=FlowDirection.TopDown,Padding=new Padding(24),WrapContents=false};message.Margin=new Padding(0,0,0,20);panel.Controls.Add(message);panel.Controls.Add(install);Controls.Add(panel);
  install.Click+=async(_,_)=>{
   if(installed){Close();return;}
   install.Enabled=false;message.Text="Preparando arquivos e verificando WebView2…";
   try{Installer.Extract(Installer.Destination);await Installer.EnsureWebView();Installer.Register();installed=true;message.Text="Instalação concluída. Abra LocalAuthor pelo menu Iniciar e importe seu arquivo de conexão.\n\nPara remover, use Aplicativos instalados no Windows.";install.Text="Fechar";install.Enabled=true;}
   catch(Exception e){message.Text="Não foi possível concluir: "+e.Message;install.Enabled=true;}
  };
 }
}
