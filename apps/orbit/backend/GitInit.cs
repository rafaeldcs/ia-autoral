public sealed partial class GitCheckout
{
    private readonly GitProcess process;
    public GitCheckout(GitProcess process)
    {
        this.process = process;
    }
}
