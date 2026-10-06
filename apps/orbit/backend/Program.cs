using System.Threading.RateLimiting;
using Microsoft.AspNetCore.RateLimiting;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json.Nodes;
using System.Text.RegularExpressions;
using Npgsql;

var runtimePath=Environment.GetEnvironmentVariable("ORBIT_RUNTIME") ?? Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"LocalAuthor","jira-experiment","runtime.json");
var runtime=JsonNode.Parse(File.ReadAllText(runtimePath))!;
var proxyToken=runtime["proxyToken"]!.GetValue<string>();
var builder=WebApplication.CreateBuilder(args);
var apiPort = Environment.GetEnvironmentVariable("ORBIT_API_PORT") ?? "5088";
if (!int.TryParse(apiPort, out var port) || port is < 1024 or > 65535) throw new InvalidOperationException("Invalid Orbit port.");
builder.WebHost.UseUrls($"http://127.0.0.1:{port}");
builder.WebHost.ConfigureKestrel(options=>options.Limits.MaxRequestBodySize=100_000);
builder.Services.AddSingleton(NpgsqlDataSource.Create(runtime["connectionString"]!.GetValue<string>()));
builder.Services.AddSingleton<Store>();
builder.Services.AddRateLimiter(o=>{o.AddFixedWindowLimiter("login",p=>{p.PermitLimit=15;p.Window=TimeSpan.FromMinutes(1);p.QueueLimit=0;});o.OnRejected=async(c,t)=>{c.HttpContext.Response.StatusCode=429;await c.HttpContext.Response.WriteAsJsonAsync(new{error="Muitas tentativas. Aguarde um minuto."},t);};});
var app=builder.Build();
app.UseRouting();app.UseRateLimiter();
app.Use(async(context,next)=>{
    var token=context.Request.Headers["X-Orbit-Token"].ToString();
    if(!CryptographicOperations.FixedTimeEquals(Encoding.UTF8.GetBytes(token),Encoding.UTF8.GetBytes(proxyToken))) {
        context.Response.StatusCode=401; await context.Response.WriteAsJsonAsync(new{error="Acesso local não autorizado."});return;
    }
    context.Response.Headers.CacheControl="no-store";
    try {
        var path=context.Request.Path.Value??"";
        if(path!="/api/health" && path!="/api/auth/status" && path!="/api/auth/login" && path!="/api/auth/setup") {
            var db=context.RequestServices.GetRequiredService<Store>();
            if(!await Accounts.Authenticate(context,db)){context.Response.StatusCode=401;await context.Response.WriteAsJsonAsync(new{error="Entre na sua conta para continuar."});return;}
            var role=Accounts.Role(context);var write=context.Request.Method!="GET";
            var admin=path.StartsWith("/api/users")||path=="/api/audit";
            var manager=(path=="/api/projects"&&write)||(path.Contains("/sprints")&&write);
            if((admin&&role!="admin")||(manager&&!Accounts.Manage(context))||(write&&role=="viewer"&&path!="/api/auth/logout")) {
                context.Response.StatusCode=403;await context.Response.WriteAsJsonAsync(new{error="Seu nível de acesso não permite esta ação."});return;
            }
        }
        await next();
    }
    catch(PostgresException ex) when(ex.SqlState=="P0001") {context.Response.StatusCode=409;await context.Response.WriteAsJsonAsync(new{error=ex.MessageText});}
    catch(PostgresException ex) when(ex.SqlState=="42501") {context.Response.StatusCode=403;await context.Response.WriteAsJsonAsync(new{error="Permissão revogada."});}
    catch(KeyNotFoundException) { context.Response.StatusCode=404;await context.Response.WriteAsJsonAsync(new{error="Registro não encontrado."}); }
    catch(PostgresException ex) when(ex.SqlState=="23505") { context.Response.StatusCode=409;await context.Response.WriteAsJsonAsync(new{error="Essa chave já está em uso."}); }
    catch(PostgresException ex) when(ex.SqlState is "23503" or "23514" or "22001") { context.Response.StatusCode=400;await context.Response.WriteAsJsonAsync(new{error="Dados incompatíveis com as regras do projeto."}); }
});
await app.Services.GetRequiredService<Store>().Initialize();
Accounts.Map(app);Planning.Map(app);Workflow.Map(app);

app.MapGet("/api/health",async(Store db)=>{
    try { await db.Query("SELECT 1::text"); return Results.Ok(new{status="ok",database="PostgreSQL",mode="local-experimental"}); }
    catch(NpgsqlException) { return Results.Json(new{error="PostgreSQL indisponível."},statusCode:503); }
});
app.MapGet("/api/projects",async(Store db)=>Results.Json(await db.Query("""
    SELECT coalesce(json_agg(r ORDER BY r.name),'[]')::text FROM (
    SELECT p.id,p.key,p.name,p.description,p.color,p.method,p.wip_limit AS "wipLimit",p.workflow_version AS "workflowVersion",
    (SELECT count(*) FROM issues i WHERE i.project_id=p.id AND NOT i.archived) AS "issueCount" FROM projects p) r
    """)));
app.MapPost("/api/projects",async(ProjectInput input,Store db,HttpContext c)=>{
    var key=input.Key?.Trim().ToUpperInvariant()??"";
    if(string.IsNullOrWhiteSpace(input.Name)||input.Name.Length>100||!Regex.IsMatch(key,"^[A-Z][A-Z0-9]{1,7}$")||(input.Description?.Length??0)>2000)
        return Results.BadRequest(new{error="Informe nome (até 100 caracteres) e chave de 2 a 8 letras/números, iniciando com letra."});
    var id=Guid.NewGuid();
    await db.Execute("INSERT INTO projects(id,key,name,description) VALUES($1,$2,$3,$4)",id,key,input.Name.Trim(),input.Description??"");
    await Accounts.Audit(db,c,"Criou projeto "+key);
    return Results.Created($"/api/projects/{id}",new{id,key,name=input.Name.Trim(),description=input.Description??"",color="#6658d9",issueCount=0,method="scrum",wipLimit=3,workflowVersion=1});
});
app.MapGet("/api/projects/{project:guid}/issues",async(Guid project,Store db)=>Results.Json(await db.Query($"SELECT coalesce(json_agg(r ORDER BY r.number),'[]')::text FROM (SELECT {Store.IssueColumns},i.number FROM issues i JOIN projects p ON p.id=i.project_id WHERE i.project_id=$1 AND NOT i.archived) r",project)));
app.MapPost("/api/projects/{project:guid}/issues",async(Guid project,IssueInput input,Store db)=>{
    var error=Validate(input);
    if(error is not null)return Results.BadRequest(new{error});
    var id=await db.Create(project,input);
    return Results.Created($"/api/issues/{id}",await db.Issue(id));
});
app.MapGet("/api/issues/{id:guid}",async(Guid id,Store db)=>{
    var issue=await db.Issue(id);
    return issue is null?Results.NotFound(new{error="Tarefa não encontrada."}):Results.Json(issue);
});
app.MapPut("/api/issues/{id:guid}",async(Guid id,IssueInput input,Store db)=>{
    var error=Validate(input);
    if(error is not null)return Results.BadRequest(new{error});
    if(input.Version is null)return Results.BadRequest(new{error="Versão do registro obrigatória."});
    var changed=await db.Query("""
        WITH changed AS (
            UPDATE issues SET title=$2,description=$3,status=$4,priority=$5,type=$6,assignee=$7,labels=$8,
            due_date=$9::date,story_points=$10::int,sprint_id=$12::uuid,version=version+1,updated_at=now()
            WHERE id=$1 AND version=$11 AND NOT archived RETURNING id),
        logged AS (INSERT INTO activity(issue_id,message) SELECT id,'Tarefa atualizada' FROM changed)
        SELECT count(*)::text FROM changed
        """,id,input.Title!.Trim(),input.Description??"",input.Status??"todo",input.Priority??"medium",input.Type??"task",input.Assignee??"",input.Labels??[],input.DueDate,input.StoryPoints,input.Version,input.SprintId);
    if(changed.GetValue<int>()==0)return Results.Conflict(new{error="A tarefa mudou em outra janela. Recarregue antes de salvar."});
    return Results.Json(await db.Issue(id));
});
app.MapGet("/api/issues/{id:guid}/comments",async(Guid id,Store db)=>Results.Json(await db.Query("SELECT coalesce(json_agg(r ORDER BY r.\"createdAt\"),'[]')::text FROM (SELECT id,author,body,created_at AS \"createdAt\" FROM comments WHERE issue_id=$1) r",id)));
app.MapPost("/api/issues/{id:guid}/comments",async(Guid id,CommentInput input,Store db,HttpContext c)=>{
    if(string.IsNullOrWhiteSpace(input.Body)||input.Body.Length>4000||(input.Author?.Length??0)>80)return Results.BadRequest(new{error="Escreva um comentário de até 4.000 caracteres."});
    if(await db.Issue(id) is null)return Results.NotFound(new{error="Tarefa não encontrada."});
    var comment=Guid.NewGuid();
    await db.Execute("INSERT INTO comments(id,issue_id,author,body) VALUES($1,$2,$3,$4)",comment,id,Accounts.Name(c),input.Body.Trim());
    return Results.Created($"/api/issues/{id}/comments/{comment}",new{id=comment});
});
app.MapGet("/api/issues/{id:guid}/activity",async(Guid id,Store db)=>Results.Json(await db.Query("SELECT coalesce(json_agg(r ORDER BY r.id DESC),'[]')::text FROM (SELECT id,message,created_at AS \"createdAt\" FROM activity WHERE issue_id=$1) r",id)));
app.MapGet("/api/experiment",()=>{
    var file=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"LocalAuthor","exports","jira-experimental","evaluation.json");
    return File.Exists(file)?Results.Json(JsonNode.Parse(File.ReadAllText(file))):Results.Ok(new{state="training",programmingQualified=false,notice="O modelo local está em avaliação. Nenhum código gerado foi aplicado ao sistema."});
});
app.MapGet("/api/experiment/complexity",()=>{
    var file=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"LocalAuthor","exports","jira-experimental","complexity-evaluation.json");
    return File.Exists(file)?Results.Json(JsonNode.Parse(File.ReadAllText(file))):Results.NotFound();
});
app.MapGet("/api/experiment/learning",()=>{
    var file=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"LocalAuthor","exports","jira-experimental","learning-report.json");
    return File.Exists(file)?Results.Json(JsonNode.Parse(File.ReadAllText(file))):Results.NotFound();
});
app.MapGet("/api/experiment/testing",()=>{
    var file=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"LocalAuthor","exports","jira-experimental","testing-report.json");
    return File.Exists(file)?Results.Json(JsonNode.Parse(File.ReadAllText(file))):Results.NotFound();
});
app.MapGet("/api/experiment/code-testing",()=>{
    var file=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"LocalAuthor","exports","jira-experimental","code-testing-report.json");
    return File.Exists(file)?Results.Json(JsonNode.Parse(File.ReadAllText(file))):Results.NotFound();
});
app.MapGet("/api/experiment/professional",()=>{
    var file=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"LocalAuthor","exports","jira-experimental","professional-report.json");
    return File.Exists(file)?Results.Json(JsonNode.Parse(File.ReadAllText(file))):Results.NotFound();
});
app.Run();

static string? Validate(IssueInput input){
    if(string.IsNullOrWhiteSpace(input.Title)||input.Title.Trim().Length>180)return "O título deve ter de 1 a 180 caracteres.";
    if((input.Description?.Length??0)>12000)return "Descrição limitada a 12.000 caracteres.";
    if(!new[]{"backlog","todo","progress","review","done"}.Contains(input.Status??"todo"))return "Status inválido.";
    if(!new[]{"low","medium","high","urgent"}.Contains(input.Priority??"medium"))return "Prioridade inválida.";
    if(!new[]{"task","story","bug"}.Contains(input.Type??"task"))return "Tipo inválido.";
    if((input.Assignee?.Length??0)>80||input.StoryPoints is <0 or >100)return "Responsável ou estimativa inválidos.";
    if((input.Labels?.Length??0)>6||input.Labels?.Any(x=>string.IsNullOrWhiteSpace(x)||x.Length>30)==true)return "Use até 6 etiquetas de 30 caracteres.";
    return null;
}
