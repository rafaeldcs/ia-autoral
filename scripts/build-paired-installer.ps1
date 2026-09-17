param([string]$DeviceName='Meu computador - instalador conectado')
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot
Set-Location $root
$lanData = Join-Path $env:LOCALAPPDATA 'LocalAuthor\lan'
$runtime = Get-Content -LiteralPath (Join-Path $lanData 'runtime.json') -Raw | ConvertFrom-Json
if (-not (Test-Path -LiteralPath (Join-Path $root 'build\client-payload.zip'))) { throw 'Execute scripts/build-lan.ps1 primeiro.' }
$packageRoot = Join-Path $lanData ('private-installers\'+[Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Force -Path $packageRoot | Out-Null
$connectionFile = Join-Path $packageRoot 'connection.localauthor'
$deviceRole = 'client'
& $runtime.Gateway add-device --data $lanData --name $DeviceName --output $connectionFile --role $deviceRole
if ($LASTEXITCODE -ne 0) { throw 'Falha ao autorizar o instalador.' }
$connection = Get-Content -LiteralPath $connectionFile -Raw | ConvertFrom-Json
try {
    $intermediate = (Join-Path $packageRoot 'obj')+'\'
    $binary = (Join-Path $packageRoot 'bin')+'\'
    $output = Join-Path $packageRoot 'output'
    & dotnet publish dotnet/LocalAuthor.Setup/LocalAuthor.Setup.csproj -c Release -r win-x64 --self-contained true -p:PublishSingleFile=true -p:IncludeNativeLibrariesForSelfExtract=true ('-p:ConnectionFile='+$connectionFile) ('-p:BaseIntermediateOutputPath='+$intermediate) ('-p:MSBuildProjectExtensionsPath='+$intermediate) ('-p:BaseOutputPath='+$binary) -o $output --nologo
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao compilar instalador conectado.' }
    $installer = Join-Path $packageRoot 'Instalar-LocalAuthor-Conectado.exe'
    Move-Item -LiteralPath (Join-Path $output 'LocalAuthor.Setup.exe') -Destination $installer
    $hash = (Get-FileHash -LiteralPath $installer -Algorithm SHA256).Hash
    ($hash+'  Instalar-LocalAuthor-Conectado.exe') | Set-Content -LiteralPath (Join-Path $packageRoot 'SHA256.txt') -Encoding ascii
    @{installer=$installer;deviceId=$connection.DeviceId;name=$DeviceName;sha256=$hash} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $packageRoot 'package.json') -Encoding UTF8
    foreach ($name in 'obj','bin','output') {
        $target = [IO.Path]::GetFullPath((Join-Path $packageRoot $name))
        if ([IO.Path]::GetDirectoryName($target) -ne [IO.Path]::GetFullPath($packageRoot)) { throw 'Destino de limpeza fora do pacote.' }
        if (Test-Path -LiteralPath $target) { Remove-Item -LiteralPath $target -Recurse -Force }
    }
    Write-Output ('Instalador privado pronto: '+$installer)
    Write-Output ('Dispositivo revogável: '+$connection.DeviceId)
} catch {
    & $runtime.Gateway revoke --data $lanData --id $connection.DeviceId | Out-Null
    throw
}
