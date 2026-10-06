public static partial class HostedEndpoints
{
    private static async Task<IResult> CreateToken(Guid project, HostedTokenInput input, Store db, HostedRepository repo, HttpContext c)
    {
        if (!await repo.Gate.WaitAsync(0, c.RequestAborted))
            return Results.Conflict(new { error = "Repositório ocupado. Tente novamente." });
        try
        {
            return await HostedTokens.Create(project, input, db, c);
        }
        finally
        {
            repo.Gate.Release();
        }
    }
}
