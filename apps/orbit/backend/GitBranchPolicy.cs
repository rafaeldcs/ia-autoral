using System;

public static partial class GitPolicy
{
    public static bool ValidBranch(string branch)
    {
        if (branch == null || branch.Length == 0 || branch.Length > 120)
            return false;

        if (!char.IsAsciiLetterOrDigit(branch[0]))
            return false;

        for (int i = 0; i < branch.Length; i++)
        {
            char c = branch[i];
            if (!char.IsAsciiLetterOrDigit(c) && c != '_' && c != '/' && c != '-')
                return false;
        }

        if (branch.Contains("//") || branch.EndsWith("/"))
            return false;

        string[] parts = branch.Split('/');
        foreach (string part in parts)
        {
            if (part.StartsWith("-"))
                return false;
        }

        return true;
    }
}
