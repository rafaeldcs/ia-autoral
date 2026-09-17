param([switch]$Install)
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot
$output = Join-Path $root 'build\server-launcher'
& dotnet publish (Join-Path $root 'dotnet\LocalAuthor.ServerLauncher\LocalAuthor.ServerLauncher.csproj') -c Release -r win-x64 --self-contained true -p:PublishSingleFile=true -p:IncludeNativeLibrariesForSelfExtract=true -o $output --nologo
if ($LASTEXITCODE -ne 0) { throw 'Falha ao compilar o aplicativo do servidor.' }
if ($Install) {
    & (Join-Path $PSScriptRoot 'lan\Install-ServerLauncher.ps1') -Executable (Join-Path $output 'LocalAuthor.ServerLauncher.exe')
}
