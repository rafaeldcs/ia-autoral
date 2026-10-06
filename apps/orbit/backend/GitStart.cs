using System.Diagnostics;
using System.Text;

public sealed partial class GitProcess {
    private static ProcessStartInfo Start(string directory, string token, string[] args) {
        var info = new ProcessStartInfo("/usr/bin/git") {
            WorkingDirectory = directory,
            UseShellExecute = false,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            CreateNoWindow = true
        };
        string[] fixedArgs = {
            "-c", "core.hooksPath=/dev/null",
            "-c", "protocol.file.allow=never",
            "-c", "protocol.ext.allow=never",
            "-c", "core.fsmonitor=false",
            "-c", "credential.helper="
        };
        foreach (var arg in fixedArgs) info.ArgumentList.Add(arg);
        foreach (var arg in args) info.ArgumentList.Add(arg);
        info.Environment.Clear();
        info.Environment["PATH"] = "/usr/bin:/bin";
        info.Environment["HOME"] = "/tmp/orbit-git";
        info.Environment["GIT_CONFIG_NOSYSTEM"] = "1";
        info.Environment["GIT_CONFIG_GLOBAL"] = "/dev/null";
        info.Environment["GIT_TERMINAL_PROMPT"] = "0";
        info.Environment["GIT_ASKPASS"] = "/bin/false";
        info.Environment["GIT_ALLOW_PROTOCOL"] = "https";
        info.Environment["GIT_LFS_SKIP_SMUDGE"] = "1";
        if (!string.IsNullOrEmpty(token)) {
            info.Environment["GIT_CONFIG_COUNT"] = "1";
            info.Environment["GIT_CONFIG_KEY_0"] = "http.https://github.com/.extraheader";
            info.Environment["GIT_CONFIG_VALUE_0"] = "Authorization: Basic " + Convert.ToBase64String(
                Encoding.UTF8.GetBytes("x-access-token:" + token)
            );
        }
        return info;
    }
}
