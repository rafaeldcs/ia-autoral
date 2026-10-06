public sealed partial class HostedRepository
{
    public async Task<object[]> Tree(Guid project, string sha, CancellationToken ct)
    {
        if (!HostedPolicy.ObjectId(sha))
        {
            throw new InvalidOperationException("SHA must not be empty.");
        }

        var output = await git.Run(DirectoryFor(project), "", ct, "ls-tree", "-z", sha);

        var entries = output.Split('\0')
                           .Where(s => !string.IsNullOrEmpty(s))
                           .Take(200)
                           .Select(line =>
                           {
                               var parts = line.Split('\t', 2);
                               if (parts.Length != 2)
                               {
                                   return null;
                               }

                               var metadata = parts[0];
                               var name = parts[1];

                               var modeTypeSha = metadata.Split(' ');
                               if (modeTypeSha.Length < 3)
                               {
                                   return null;
                               }

                               return new
                               {
                                   mode = modeTypeSha[0],
                                   type = modeTypeSha[1],
                                   sha = modeTypeSha[2],
                                   name = name
                               };
                           })
                           .Where(e => e != null).Cast<object>().ToArray();

        return entries;
    }
}
