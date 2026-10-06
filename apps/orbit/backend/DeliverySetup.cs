using Microsoft.AspNetCore.DataProtection;
using System;
using System.IO;
using Microsoft.Extensions.DependencyInjection;

public static class DeliverySetup
{
    public static void Services(WebApplicationBuilder builder)
    {
        string keys = Environment.GetEnvironmentVariable("ORBIT_KEYS_DIR") ?? Path.Combine(Path.GetTempPath(), "orbit-keys");
        if (!Path.IsPathFullyQualified(keys))
            throw new Exception("Keys directory path must be fully qualified.");
        Directory.CreateDirectory(keys);
        builder.Services.AddDataProtection().PersistKeysToFileSystem(new DirectoryInfo(keys)).SetApplicationName("Orbit");
        builder.Services.AddSingleton<GitProcess>();
        builder.Services.AddSingleton<GitCheckout>();
        builder.Services.AddSingleton<GitHubDelivery>();
        builder.Services.AddHostedService<GitWorker>();
    }

    public static bool SetupAllowed() => Environment.GetEnvironmentVariable("ORBIT_DISABLE_SETUP") != "1";

    public static string Bind()
    {
        var bind = Environment.GetEnvironmentVariable("ORBIT_BIND");
        if (string.IsNullOrEmpty(bind) || bind=="127.0.0.1")
            return "127.0.0.1";
        if (bind == "0.0.0.0")
            return "0.0.0.0";
        throw new Exception("Invalid bind address.");
    }
}
