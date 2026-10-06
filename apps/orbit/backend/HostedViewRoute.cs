using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.Abstractions;
using Microsoft.AspNetCore.Mvc.Filters;
using Microsoft.AspNetCore.Routing;
using System;
using System.Threading.Tasks;

public static partial class HostedEndpoints
{
    private static async Task<IResult> View(Guid project, Store db, HostedRepository repo, HttpContext c)
    {
        if (!await repo.Gate.WaitAsync(0, c.RequestAborted)) return Results.Conflict(new { error = "Repositório ocupado. Tente novamente." });
        try { return Results.Json(await repo.View(project, db, c.RequestAborted)); }
        finally { repo.Gate.Release(); }
    }
}
