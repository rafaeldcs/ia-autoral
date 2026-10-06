using System.Diagnostics;
using System.Text.Json;

public sealed class GitCheckoutTests
{
    private sealed class Fixture : IDisposable
    {
        public readonly string Root=Path.Combine(Path.GetTempPath(),"orbit-checkout-"+Guid.NewGuid().ToString("N"));
        public readonly Guid Project=Guid.NewGuid();
        public readonly string Url="https://github.com/team/nonexistent-orbit-qa-fixture.git";
        public string DirectoryPath=>Path.Combine(Root,Project.ToString("N"));
        public string Head=>Git("rev-parse","HEAD");
        private readonly string? previous=Environment.GetEnvironmentVariable("ORBIT_REPOSITORIES");
        public Fixture()
        {
            Directory.CreateDirectory(DirectoryPath);
            Environment.SetEnvironmentVariable("ORBIT_REPOSITORIES",Root);
            Git("init","-b","main");Git("config","user.email","fixture@example.invalid");Git("config","user.name","Orbit QA");
            File.WriteAllText(Path.Combine(DirectoryPath,"file.txt"),"synthetic fixture");
            Git("add","file.txt");Git("commit","-m","ORB-1 Entrega de teste");Git("remote","add","origin",Url);
        }
        public string Git(params string[] args)
        {
            var info=new ProcessStartInfo("/usr/bin/git"){WorkingDirectory=DirectoryPath,UseShellExecute=false,RedirectStandardOutput=true,RedirectStandardError=true};
            foreach(var arg in args)info.ArgumentList.Add(arg);
            using var process=Process.Start(info)!;
            var output=process.StandardOutput.ReadToEnd();var error=process.StandardError.ReadToEnd();
            Assert.True(process.WaitForExit(10000));Assert.Equal(0,process.ExitCode);return output.Trim();
        }
        public Task<(string Head,string Commits)> Run(string action,string? head=null)=>new GitCheckout(new GitProcess()).Execute(Project,Url,"main","",action,head??Head,CancellationToken.None);
        public void Dispose(){Environment.SetEnvironmentVariable("ORBIT_REPOSITORIES",previous);Directory.Delete(Root,true);}
    }
    [Fact] public async Task DeploymentChecksRevisionWithoutPushing(){using var f=new Fixture();var result=await f.Run("deploy");Assert.Equal(f.Head,result.Head);using var commits=JsonDocument.Parse(result.Commits);Assert.Equal("ORB-1 Entrega de teste",commits.RootElement[0].GetProperty("subject").GetString());}
    [Fact] public async Task DirtyTreeIsRejected(){using var f=new Fixture();File.AppendAllText(Path.Combine(f.DirectoryPath,"file.txt"),"change");await Assert.ThrowsAsync<InvalidOperationException>(()=>f.Run("deploy"));}
    [Fact] public async Task StaleRevisionIsRejected(){using var f=new Fixture();await Assert.ThrowsAsync<InvalidOperationException>(()=>f.Run("deploy",new string('a',40)));}
    [Fact] public async Task ChangedBranchIsRejected(){using var f=new Fixture();f.Git("checkout","-b","other");await Assert.ThrowsAsync<InvalidOperationException>(()=>f.Run("deploy"));}
    [Fact] public async Task ChangedRemoteIsRejected(){using var f=new Fixture();f.Git("remote","set-url","origin","https://github.com/team/other.git");await Assert.ThrowsAsync<InvalidOperationException>(()=>f.Run("deploy"));}
    [Fact] public async Task PushActuallyContactsRemoteAndFailsClosedWithoutNetwork(){using var f=new Fixture();await Assert.ThrowsAsync<InvalidOperationException>(()=>f.Run("push"));Assert.Equal(f.Head,f.Git("rev-parse","HEAD"));}
    [Fact] public async Task UnknownActionIsRejected(){using var f=new Fixture();await Assert.ThrowsAnyAsync<ArgumentException>(()=>f.Run("delete"));}
    [Fact] public async Task RelativeRootIsRejected(){using var f=new Fixture();Environment.SetEnvironmentVariable("ORBIT_REPOSITORIES","relative-folder");await Assert.ThrowsAsync<InvalidOperationException>(()=>f.Run("deploy"));}
}
