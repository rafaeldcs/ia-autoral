using System.Security.Cryptography;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;


public static partial class HostedTokens
{
    public static async Task<IResult> Create(Guid project, HostedTokenInput input, Store db, HttpContext c)
    {
        var label = input.Label?.Trim();
        if (string.IsNullOrEmpty(label) || label.Length > 80 || label.Any(char.IsControl))
            return Results.BadRequest(new { error = "Label inválida" });

        var role = Accounts.Role(c);
        if (input.Write && !HostedPolicy.CanWrite(role))
            return Results.Json(new { error = "Acesso negado" }, statusCode: 403);

        var repo = c.RequestServices.GetRequiredService<HostedRepository>();
        if (!await repo.RepositoryExists(project, db))
            return Results.NotFound();

        var userGuid = Guid.Parse(Accounts.User(c)["id"]!.GetValue<string>());
        if ((await CountActive(project, userGuid, db)) >= 20)
            return Results.Conflict();

        var id = Guid.NewGuid();
        var tokenBytes = RandomNumberGenerator.GetBytes(32);
        var token = "orb_" + Convert.ToHexString(tokenBytes).ToLowerInvariant();
        var hash = Accounts.Hash(token);

        await db.Execute(
            "INSERT INTO hosted_tokens(id,project_id,user_id,hash,label,write_access) VALUES($1,$2,$3,$4,$5,$6)",
            id, project, userGuid, hash, label, input.Write);

        await Accounts.Audit(db, c, "create with id " + id);
        return Results.Json(new { id, token, expiresInDays = 30 }, statusCode: 201);
    }
}

public sealed record HostedTokenInput(string? Label, bool Write = false);
