using System.Security.Cryptography;
using System.Text;
using System.Text.Json.Nodes;
using Microsoft.AspNetCore.Identity;

public static class Accounts
{
    private static readonly PasswordHasher<string> Hasher = new();
    public static string Hash(string value)=>Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(value)));
    public static JsonNode User(HttpContext c)=>(JsonNode)c.Items["account"]!;
    public static string Role(HttpContext c)=>User(c)["role"]!.GetValue<string>();
    public static string Name(HttpContext c)=>User(c)["name"]!.GetValue<string>();
    public static bool Manage(HttpContext c)=>Role(c) is "admin" or "manager";
    public static string? Validate(UserInput u)=>string.IsNullOrWhiteSpace(u.Name)||u.Name.Length>80||string.IsNullOrWhiteSpace(u.Email)||u.Email.Length>160||!u.Email.Contains('@')||u.Password is null||u.Password.Length<12||u.Password.Length>128||!new[]{"admin","manager","member","viewer"}.Contains(u.Role)?"Nome, e-mail, papel e senha de 12 a 128 caracteres são obrigatórios.":null;
    public static Task Audit(Store db,HttpContext c,string action)=>db.Execute("INSERT INTO audit(actor,action) VALUES($1,$2)",Name(c),action);
    public static async Task<bool> Authenticate(HttpContext c,Store db) {
        var token=c.Request.Cookies["orbit_session"];
        if(token is null||token.Length>128)return false;
        var user=await db.Query("SELECT row_to_json(u)::text FROM (SELECT u.id,u.name,u.email,u.role FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.hash=$1 AND s.expires_at>now() AND u.active) u",Hash(token));
        if(user is null)return false;
        c.Items["account"]=user;return true;
    }
    private static async Task Session(Store db,HttpContext c,Guid id) {
        var token=Convert.ToHexString(RandomNumberGenerator.GetBytes(32));
        await db.Execute("INSERT INTO sessions(hash,user_id,expires_at) VALUES($1,$2,now()+interval '8 hours')",Hash(token),id);
        c.Response.Cookies.Append("orbit_session",token,new CookieOptions{HttpOnly=true,SameSite=SameSiteMode.Strict,Secure=Environment.GetEnvironmentVariable("ORBIT_PUBLIC_ORIGIN") is not null,Path="/",MaxAge=TimeSpan.FromHours(8)});
    }
    public static void Map(WebApplication app) {
        app.MapGet("/api/auth/status",async(Store db)=>Results.Ok(new{setup=!(await db.Query("SELECT EXISTS(SELECT 1 FROM users)::text")).GetValue<bool>()}));
        app.MapPost("/api/auth/setup",async(UserInput input,Store db,HttpContext c)=>{
if(!DeliverySetup.SetupAllowed())return Results.Json(new{error="Configuração inicial reservada ao administrador do servidor."},statusCode:403);
            input=input with{Role="admin"};var error=Validate(input);if(error is not null)return Results.BadRequest(new{error});
            var id=Guid.NewGuid();
            var result=await db.Query("""
                WITH lock AS MATERIALIZED (SELECT pg_advisory_xact_lock(729381)), inserted AS (
                INSERT INTO users(id,name,email,password_hash,role,bootstrap)
                SELECT $1,$2,$3,$4,'admin',true FROM lock WHERE NOT EXISTS(SELECT 1 FROM users) RETURNING id)
                SELECT count(*)::text FROM inserted
                """,id,input.Name!.Trim(),input.Email!.Trim().ToLowerInvariant(),Hasher.HashPassword("",input.Password!));
            if(result.GetValue<int>()==0)return Results.Conflict(new{error="O administrador já foi configurado."});
            await Session(db,c,id);return Results.Ok(new{ok=true});
        }).RequireRateLimiting("login");
        app.MapPost("/api/auth/login",async(LoginInput input,Store db,HttpContext c)=>{
            if(input.Password is null||input.Password.Length>128||input.Email is null||input.Email.Length>160)return Results.BadRequest(new{error="Credenciais inválidas."});
            var user=await db.Query("SELECT row_to_json(u)::text FROM (SELECT id,password_hash FROM users WHERE email=$1 AND active) u",input.Email.Trim().ToLowerInvariant());
            // A fixed dummy hash still performs password work for unknown accounts.
            var hash=user?["password_hash"]?.GetValue<string>()??DummyHash;
            if(Hasher.VerifyHashedPassword("",hash,input.Password)==PasswordVerificationResult.Failed||user is null)return Results.Json(new{error="E-mail ou senha inválidos."},statusCode:401);
            await Session(db,c,Guid.Parse(user["id"]!.GetValue<string>()));return Results.Ok(new{ok=true});
        }).RequireRateLimiting("login");
        app.MapGet("/api/auth/me",(HttpContext c)=>Results.Json(User(c)));
        app.MapPost("/api/auth/logout",async(Store db,HttpContext c)=>{
            await db.Execute("DELETE FROM sessions WHERE hash=$1",Hash(c.Request.Cookies["orbit_session"]??""));c.Response.Cookies.Delete("orbit_session");return Results.Ok(new{ok=true});
        });
        app.MapGet("/api/people",async(Store db)=>Results.Json(await db.Query("SELECT coalesce(json_agg(u ORDER BY name),'[]')::text FROM (SELECT id,name FROM users WHERE active) u")));
        app.MapGet("/api/users",async(Store db)=>Results.Json(await db.Query("SELECT coalesce(json_agg(u ORDER BY name),'[]')::text FROM (SELECT id,name,email,role,active FROM users) u")));
        app.MapPost("/api/users",async(UserInput input,Store db,HttpContext c)=>{
            var error=Validate(input);if(error is not null)return Results.BadRequest(new{error});
            var id=Guid.NewGuid();await db.Execute("INSERT INTO users(id,name,email,password_hash,role) VALUES($1,$2,$3,$4,$5)",id,input.Name!.Trim(),input.Email!.Trim().ToLowerInvariant(),Hasher.HashPassword("",input.Password!),input.Role);
            await Audit(db,c,"Criou usuário "+input.Email);return Results.Created("/api/users/"+id,new{id});
        });
        app.MapPut("/api/users/{id:guid}",async(Guid id,RoleInput input,Store db,HttpContext c)=>{
            if(!new[]{"admin","manager","member","viewer"}.Contains(input.Role))return Results.BadRequest(new{error="Papel inválido."});
            if(User(c)["id"]!.GetValue<string>()==id.ToString())return Results.BadRequest(new{error="Peça a outro administrador para alterar sua conta."});
            var changed=await db.Query("SELECT configure_user($1,$2,$3,$4)::text",Guid.Parse(User(c)["id"]!.GetValue<string>()),id,input.Role,input.Active);
            if(!changed.GetValue<bool>())return Results.NotFound();
            await Audit(db,c,"Alterou permissões do usuário "+id);return Results.Ok(new{ok=true});
        });
        app.MapGet("/api/audit",async(Store db)=>Results.Json(await db.Query("SELECT coalesce(json_agg(a ORDER BY id DESC),'[]')::text FROM (SELECT id,actor,action,created_at AS \"createdAt\" FROM audit ORDER BY id DESC LIMIT 100) a")));
    }
    private static readonly string DummyHash=Hasher.HashPassword("",Convert.ToHexString(RandomNumberGenerator.GetBytes(32)));
}
public sealed record UserInput(string? Name,string? Email,string? Password,string Role="member");
public sealed record LoginInput(string? Email,string? Password);
public sealed record RoleInput(string Role,bool Active);
