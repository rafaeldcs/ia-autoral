using System.Net;
using System.Reflection;
using System.Text;
using System.Text.Json;

public sealed class GitDeliveryTests
{
    private sealed class Handler(string conclusion) : HttpMessageHandler
    {
        public int Reruns;
        protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request,CancellationToken token)
        {
            Assert.Equal("api.github.com",request.RequestUri!.Host);
            if(request.Method==HttpMethod.Post){Reruns++;throw new Exception("Recovery must never redeploy");}
            var body=JsonSerializer.Serialize(new{workflow_runs=new[]{new{id=123L,head_sha=new string('a',40),head_branch="codex/local-learning-execution",status="completed",conclusion,run_attempt=1,html_url="https://github.com/rafaeldcs/ia-autoral/actions/runs/123"}}});
            return Task.FromResult(new HttpResponseMessage(HttpStatusCode.OK){Content=new StringContent(body,Encoding.UTF8,"application/json")});
        }
    }
    private static Task<string> Watch(HttpClient client)=>
        (Task<string>)typeof(GitHubDelivery).GetMethod("Watch",BindingFlags.NonPublic|BindingFlags.Static)!.Invoke(null,new object[]{client,"codex/local-learning-execution",new string('a',40),CancellationToken.None,false})!;
    [Fact] public async Task ResumeCompletedDeliveryDoesNotRerun()
    {
        using var handler=new Handler("success");using var client=new HttpClient(handler);
        Assert.Equal("https://github.com/rafaeldcs/ia-autoral/actions/runs/123",await Watch(client));Assert.Equal(0,handler.Reruns);
    }
    [Fact] public async Task ResumeFailedDeliveryCannotSucceed()
    {
        using var handler=new Handler("failure");using var client=new HttpClient(handler);
        await Assert.ThrowsAnyAsync<Exception>(()=>Watch(client));Assert.Equal(0,handler.Reruns);
    }
    [Theory]
    [InlineData("https://github.com/other/repo.git","codex/local-learning-execution","aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")]
    [InlineData("https://github.com/rafaeldcs/ia-autoral.git","main","aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")]
    [InlineData("https://github.com/rafaeldcs/ia-autoral.git","codex/local-learning-execution","HEAD")]
    public async Task UnapprovedDeliveryRejectedBeforeNetwork(string url,string branch,string sha)=>
        await Assert.ThrowsAsync<InvalidOperationException>(()=>new GitHubDelivery().Run(url,branch,sha,"synthetic-token",CancellationToken.None));
}
