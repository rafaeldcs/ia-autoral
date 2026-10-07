using System;
using System.Diagnostics;
using System.Globalization;

public static class HostedHttpStart
{
    public static ProcessStartInfo Build(string root, Guid project, string endpoint, string query, string method, string contentType, long length, string actor, string protocol)
    {
        var p = new ProcessStartInfo("/usr/bin/git")
        {
            UseShellExecute = false,
            RedirectStandardInput = true,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            WorkingDirectory = root
        };

        string[] args = {
            "-c", "core.hooksPath=/dev/null",
            "-c", "protocol.ext.allow=never",
            "-c", "protocol.file.allow=never",
            "-c", "http.getanyfile=false",
            "-c", "receive.denyNonFastForwards=true",
            "-c", "receive.denyDeletes=true",
            "-c", "receive.maxInputSize=20971520",
            "-c", "gc.auto=0",
            "http-backend"
        };

        foreach (var arg in args)
        {
            p.ArgumentList.Add(arg);
        }

        p.Environment.Clear();
        p.Environment["PATH"] = "/usr/bin:/bin";
        p.Environment["HOME"] = "/tmp/orbit-git";
        p.Environment["GIT_CONFIG_NOSYSTEM"] = "1";
        p.Environment["GIT_CONFIG_GLOBAL"] = "/dev/null";
        p.Environment["GIT_TERMINAL_PROMPT"] = "0";
        p.Environment["GIT_PROJECT_ROOT"] = root;
        p.Environment["GIT_HTTP_EXPORT_ALL"] = "1";
        p.Environment["PATH_INFO"] = $"/{project.ToString("D")}.git/{endpoint}";
        p.Environment["QUERY_STRING"] = query;
        p.Environment["REQUEST_METHOD"] = method;
        p.Environment["CONTENT_TYPE"] = contentType;
        p.Environment["CONTENT_LENGTH"] = length.ToString(CultureInfo.InvariantCulture);
        p.Environment["REMOTE_USER"] = actor;

        if (protocol == "version=2")
        {
            p.Environment["HTTP_GIT_PROTOCOL"] = protocol;
        }

        return p;
    }
}
