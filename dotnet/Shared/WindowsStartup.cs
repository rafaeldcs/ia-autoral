using Microsoft.Win32;

namespace LocalAuthor.Connectivity;

static class WindowsStartup {
 const string RunPath=@"Software\Microsoft\Windows\CurrentVersion\Run";
 const string SettingsPath=@"Software\LocalAuthorClient";
 public static string InstalledExecutable=>Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"Programs","LocalAuthorClient","LocalAuthor.Client.exe");
 public static bool Preferred {get{using var settings=Registry.CurrentUser.OpenSubKey(SettingsPath);return settings?.GetValue("StartWithWindows") is not int value||value!=0;}}
 public static void Configure(string executable,bool enabled){
  using var run=Registry.CurrentUser.CreateSubKey(RunPath);
  using var settings=Registry.CurrentUser.CreateSubKey(SettingsPath);
  Configure(executable,enabled,run,settings);
 }
 internal static void Configure(string executable,bool enabled,RegistryKey run,RegistryKey settings){
  executable=Path.GetFullPath(executable);
  if(enabled&&!File.Exists(executable))throw new FileNotFoundException("Instale o aplicativo antes de ativar a abertura automática.");
  if(enabled)run.SetValue("LocalAuthorClient","\""+executable+"\" --startup",RegistryValueKind.String);
  else run.DeleteValue("LocalAuthorClient",false);
  settings.SetValue("StartWithWindows",enabled?1:0,RegistryValueKind.DWord);
 }
 internal static void EnsureDefault(string executable,RegistryKey run,RegistryKey settings){
  if(settings.GetValue("StartWithWindows")==null)Configure(executable,true,run,settings);
 }
 public static void EnsureInstalledDefault(){
  // Updates also enable startup for existing installations, never for build/test/temporary executables.
  if(!string.Equals(Environment.ProcessPath,InstalledExecutable,StringComparison.OrdinalIgnoreCase))return;
  using var run=Registry.CurrentUser.CreateSubKey(RunPath);
  using var settings=Registry.CurrentUser.CreateSubKey(SettingsPath);
  EnsureDefault(InstalledExecutable,run,settings);
 }
 public static object CheckInIsolatedRegistry(string executable){
  var path=@"Software\LocalAuthorStartupCheck-"+Guid.NewGuid().ToString("N");
  try{
   using var root=Registry.CurrentUser.CreateSubKey(path);
   using var run=root.CreateSubKey("Run");using var settings=root.CreateSubKey("Settings");
   run.SetValue("UnrelatedApplication","preserve");
   EnsureDefault(executable,run,settings);
   var command=run.GetValue("LocalAuthorClient") as string;
   bool registered=command=="\""+Path.GetFullPath(executable)+"\" --startup";
   Configure(executable,false,run,settings);EnsureDefault(executable,run,settings);
   bool optOutPreserved=run.GetValue("LocalAuthorClient")==null&&(int)settings.GetValue("StartWithWindows")! ==0;
   bool unrelated=Equals(run.GetValue("UnrelatedApplication"),"preserve");
   return new{passed=registered&&optOutPreserved&&unrelated,registered,optOutPreserved,unrelated,command};
  }finally{Registry.CurrentUser.DeleteSubKeyTree(path,false);}
 }
}
