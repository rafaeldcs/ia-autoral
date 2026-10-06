using System.Diagnostics;
using System.Reflection;
using System.Text;

public sealed class GitPolicyTests
{
    [Theory]
    [InlineData("https://github.com/rafaeldcs/ia-autoral.git",true)]
    [InlineData("https://github.com/team/project.git",true)]
    [InlineData("https://github.com/team/.git",false)]
    [InlineData("https://github.com/team/..git",false)]
    [InlineData("https://github.com/team/...git",false)]
    [InlineData("https://github.com/team/project.git.git",false)]
    [InlineData("https://github.com/team/project.git\n",false)]
    [InlineData("https://token@github.com/team/project.git",false)]
    [InlineData("https://github.com:443/team/project.git",false)]
    [InlineData("https://github.com.evil.test/team/project.git",false)]
    [InlineData("http://github.com/team/project.git",false)]
    [InlineData("file:///tmp/repo",false)]
    [InlineData("https://github.com/team/project.git?token=x",false)]
    [InlineData("https://github.com/team/project.git#x",false)]
    [InlineData("https://github.com/team/%2e.git",false)]
    public void CanonicalRepository(string url,bool expected)=>Assert.Equal(expected,GitPolicy.ValidUrl(url));

    [Theory]
    [InlineData("main",true)]
    [InlineData("codex/local-learning-execution",true)]
    [InlineData("release_2",true)]
    [InlineData("a//b",false)]
    [InlineData("a/-b",false)]
    [InlineData("a/",false)]
    [InlineData("/a",false)]
    [InlineData("-main",false)]
    [InlineData("main\n",false)]
    [InlineData("main\r",false)]
    [InlineData("a b",false)]
    [InlineData("a..b",false)]
    [InlineData("a@{b}",false)]
    [InlineData("a\\b",false)]
    public void BranchBoundary(string branch,bool expected)=>Assert.Equal(expected,GitPolicy.ValidBranch(branch));

    [Fact] public void LengthBoundary(){Assert.True(GitPolicy.ValidBranch(new string('a',120)));Assert.False(GitPolicy.ValidBranch(new string('a',121)));}
    [Fact] public void ExactRevision(){Assert.True(GitPolicy.ValidSha(new string('a',40)));Assert.False(GitPolicy.ValidSha(new string('a',40)+"\n"));Assert.False(GitPolicy.ValidSha(new string('A',40)));Assert.False(GitPolicy.ValidSha("HEAD"));}
    [Fact] public void DeploymentScope(){Assert.Null(GitPolicy.Validate("https://github.com/rafaeldcs/ia-autoral.git","codex/local-learning-execution","orbit-hml.yml",true));Assert.NotNull(GitPolicy.Validate("https://github.com/other/repo.git","main","orbit-hml.yml",true));Assert.NotNull(GitPolicy.Validate("https://github.com/rafaeldcs/ia-autoral.git","main","orbit-hml.yml",true));Assert.Null(GitPolicy.Validate("https://github.com/other/repo.git","main","orbit-hml.yml",false));}
    [Theory] [InlineData("admin",true)] [InlineData("manager",true)] [InlineData("member",false)] [InlineData("viewer",false)] [InlineData("super",false)]
    public void Roles(string role,bool expected)=>Assert.Equal(expected,GitPolicy.CanManage(role));

    [Fact]
    public void ChildEnvironmentAndArgumentsAreIsolated()
    {
        Environment.SetEnvironmentVariable("ORBIT_TEST_PRIVATE","must-not-inherit");
        var method=typeof(GitProcess).GetMethod("Start",BindingFlags.Static|BindingFlags.NonPublic)!;
        var info=(ProcessStartInfo)method.Invoke(null,new object[]{"/tmp","synthetic-token",new[]{"log","--format=a b"}})!;
        Assert.False(info.UseShellExecute);Assert.Empty(info.Arguments);
        Assert.Equal("--format=a b",info.ArgumentList.Last());
        Assert.Contains("core.hooksPath=/dev/null",info.ArgumentList);
        Assert.Contains("protocol.file.allow=never",info.ArgumentList);
        Assert.False(info.Environment.ContainsKey("ORBIT_TEST_PRIVATE"));
        Assert.DoesNotContain(info.ArgumentList,x=>x.Contains("synthetic-token"));
        Assert.Equal("Authorization: Basic "+Convert.ToBase64String(Encoding.UTF8.GetBytes("x-access-token:synthetic-token")),info.Environment["GIT_CONFIG_VALUE_0"]);
        Environment.SetEnvironmentVariable("ORBIT_TEST_PRIVATE",null);
    }
    [Fact]
    public async Task OutputIsBoundedAndFullyDrained()
    {
        using var stream=new MemoryStream(Encoding.UTF8.GetBytes(new string('x',100000)));
        using var reader=new StreamReader(stream);
        var method=typeof(GitProcess).GetMethod("Read",BindingFlags.Static|BindingFlags.NonPublic)!;
        var result=await (Task<string>)method.Invoke(null,new object[]{reader,CancellationToken.None})!;
        Assert.Equal(32768,result.Length);Assert.Equal(stream.Length,stream.Position);
    }
    [Fact]
    public async Task RealGitExecutesWithoutShell()
    {
        var result=await new GitProcess().Run("/tmp","",CancellationToken.None,"--version");
        Assert.StartsWith("git version ",result);
        var error=await Assert.ThrowsAsync<InvalidOperationException>(()=>new GitProcess().Run("/tmp","synthetic-secret",CancellationToken.None,"--unknown-option"));
        Assert.DoesNotContain("synthetic-secret",error.Message);
    }
}
