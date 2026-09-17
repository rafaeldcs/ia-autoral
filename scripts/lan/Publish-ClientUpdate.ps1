param([string]$ClientPath, [string]$DataRoot = (Join-Path $env:LOCALAPPDATA 'LocalAuthor\lan'))
$ErrorActionPreference = 'Stop'
function Get-ReleaseHash([string]$Path) {
    $algorithm = [Security.Cryptography.SHA256]::Create()
    $stream = [IO.File]::OpenRead($Path)
    try { return [BitConverter]::ToString($algorithm.ComputeHash($stream)).Replace('-','') }
    finally { $stream.Dispose(); $algorithm.Dispose() }
}
if (-not $ClientPath) { $ClientPath = Join-Path (Split-Path (Split-Path $PSScriptRoot)) 'build\lan-client\LocalAuthor.Client.exe' }
$ClientPath = (Resolve-Path -LiteralPath $ClientPath).Path
$source = Get-Item -LiteralPath $ClientPath
if ($source.Length -lt 1 -or $source.Length -gt 300MB) { throw 'Tamanho de cliente invalido.' }
$version = [Version]$source.VersionInfo.FileVersion
$hash = Get-ReleaseHash $ClientPath
$releases = Join-Path $DataRoot 'client-releases'
New-Item -ItemType Directory -Force -Path $releases | Out-Null
$publicationLock = [IO.File]::Open((Join-Path $releases 'publish.lock'),[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
try {
$current = Join-Path $releases 'current.json'
if (Test-Path -LiteralPath $current) {
    $previous = Get-Content -LiteralPath $current -Raw | ConvertFrom-Json
    if ([Version]$previous.Version -ge $version) {
        if ($previous.Sha256 -eq $hash -and [Version]$previous.Version -eq $version) { Write-Output 'Esta versao ja esta publicada.'; exit 0 }
        throw 'Incremente Version no projeto do cliente e recompile. Publicacao antiga ou versao reutilizada recusada.'
    }
}
$package = Join-Path $releases ($hash+'.exe')
if (-not (Test-Path -LiteralPath $package)) { Copy-Item -LiteralPath $ClientPath -Destination $package }
if ((Get-ReleaseHash $package) -ne $hash) { throw 'Integridade do pacote publicado invalida.' }
$manifest = @{Version=$version.ToString();Sha256=$hash;Size=$source.Length} | ConvertTo-Json
$pending = Join-Path $releases ('manifest-'+[Guid]::NewGuid().ToString('N')+'.tmp')
[IO.File]::WriteAllText($pending,$manifest,[Text.UTF8Encoding]::new($false))
if (Test-Path -LiteralPath $current) { [IO.File]::Replace($pending,$current,($current+'.previous')) } else { [IO.File]::Move($pending,$current) }
Write-Output ('Cliente '+$version+' publicado. Aplicativos conectados verificam a cada 5 minutos.')
} finally { $publicationLock.Dispose() }
