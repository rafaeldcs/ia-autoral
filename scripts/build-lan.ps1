$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot
Set-Location $root
New-Item -ItemType Directory -Force build/downloads,build/lan-client,build/lan-server,dist/lan | Out-Null
$webview = Join-Path $root 'build/downloads/MicrosoftEdgeWebView2RuntimeInstallerX64.exe'
if (-not (Test-Path -LiteralPath $webview)) { Invoke-WebRequest 'https://go.microsoft.com/fwlink/?linkid=2124701' -OutFile $webview }
$signature = Get-AuthenticodeSignature -LiteralPath $webview
if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notlike '*Microsoft Corporation*') { throw 'Assinatura do WebView2 inválida.' }
foreach ($component in @(@('LocalAuthor.Lan','build/lan-server'),@('LocalAuthor.Client','build/lan-client'))) {
    & dotnet publish ('dotnet/'+$component[0]+'/'+$component[0]+'.csproj') -c Release -r win-x64 --self-contained true -p:PublishSingleFile=true -p:IncludeNativeLibrariesForSelfExtract=true -o $component[1] --nologo
    if ($LASTEXITCODE -ne 0) { throw ('Falha ao publicar '+$component[0]) }
}
& .venv/Scripts/python.exe scripts/lan/package-payload.py
if ($LASTEXITCODE -ne 0) { throw 'Falha ao preparar payload.' }
& dotnet publish dotnet/LocalAuthor.Setup/LocalAuthor.Setup.csproj -c Release -r win-x64 --self-contained true -p:PublishSingleFile=true -p:IncludeNativeLibrariesForSelfExtract=true -o build/lan-setup --nologo
if ($LASTEXITCODE -ne 0) { throw 'Falha ao gerar instalador.' }
Copy-Item -LiteralPath build/lan-setup/LocalAuthor.Setup.exe -Destination dist/lan/Instalar-LocalAuthor-Windows-x64.exe
Get-FileHash -Algorithm SHA256 dist/lan/Instalar-LocalAuthor-Windows-x64.exe | Format-List
