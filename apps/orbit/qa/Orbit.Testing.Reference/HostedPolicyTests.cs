public sealed class HostedPolicyTests
{
    [Theory]
    [InlineData("GET","info/refs","service=git-upload-pack","upload-pack")]
    [InlineData("GET","info/refs","service=git-receive-pack","receive-pack")]
    [InlineData("POST","git-upload-pack","","upload-pack")]
    [InlineData("POST","git-receive-pack","","receive-pack")]
    [InlineData("GET","info/refs","service=git-upload-pack&extra=x",null)]
    [InlineData("GET","info/refs","service=git-upload-pack\n",null)]
    [InlineData("GET","HEAD","",null)]
    [InlineData("POST","git-receive-pack","service=git-receive-pack",null)]
    [InlineData("PUT","git-receive-pack","",null)]
    public void OnlySmartProtocol(string method,string endpoint,string query,string? expected)
        =>Assert.Equal(expected,HostedPolicy.Service(method,endpoint,query));

    [Theory]
    [InlineData("admin",true,true)]
    [InlineData("manager",true,true)]
    [InlineData("member",true,false)]
    [InlineData("viewer",false,false)]
    [InlineData("unknown",false,false)]
    public void WorkspaceRoles(string role,bool write,bool create)
    {
        Assert.Equal(write,HostedPolicy.CanWrite(role));Assert.Equal(create,HostedPolicy.CanCreate(role));
    }
    [Fact]
    public void ObjectNamesMustBeImmutableExactHashes()
    {
        var valid=new string('a',40);Assert.True(HostedPolicy.ObjectId(valid));
        foreach(var bad in new[]{valid+"\n",valid+" ","../config",valid.ToUpperInvariant(),"--help","HEAD"})Assert.False(HostedPolicy.ObjectId(bad));
    }
    [Fact]
    public void CgiUsesFixedExecutableNoShellAndNoCredentialEnvironment()
    {
        var id=Guid.NewGuid();var p=HostedHttpStart.Build("/tmp/hosted",id,"info/refs","service=git-upload-pack","GET","",0,"qa@orbit.test","version=2");
        Assert.Equal("/usr/bin/git",p.FileName);Assert.False(p.UseShellExecute);
        Assert.Equal("http-backend",p.ArgumentList.Last());Assert.Equal("/"+id+".git/info/refs",p.Environment["PATH_INFO"]);
        Assert.Equal("/tmp/hosted",p.Environment["GIT_PROJECT_ROOT"]);
        Assert.Equal("version=2",p.Environment["HTTP_GIT_PROTOCOL"]);
        Assert.Contains("core.hooksPath=/dev/null",p.ArgumentList);
        Assert.Contains("receive.denyNonFastForwards=true",p.ArgumentList);
        Assert.DoesNotContain(p.Environment.Keys,k=>k.Contains("AUTH",StringComparison.OrdinalIgnoreCase)||k.Contains("TOKEN",StringComparison.OrdinalIgnoreCase));
        var bad=HostedHttpStart.Build("/tmp/hosted",id,"info/refs","","GET","",0,"qa@orbit.test","version=2\nEVIL=1");
        Assert.False(bad.Environment.ContainsKey("HTTP_GIT_PROTOCOL"));
    }
}
