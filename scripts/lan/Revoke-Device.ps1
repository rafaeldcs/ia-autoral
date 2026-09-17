param([string]$Id)
$ErrorActionPreference = 'Stop'
$dataRoot = Join-Path $env:LOCALAPPDATA 'LocalAuthor\lan'
$runtime = Get-Content -LiteralPath (Join-Path $dataRoot 'runtime.json') -Raw | ConvertFrom-Json
& $runtime.Gateway list --data $dataRoot
if (-not $Id) { $Id = Read-Host 'Identificador do dispositivo a revogar' }
& $runtime.Gateway revoke --data $dataRoot --id $Id
if ($LASTEXITCODE -ne 0) { throw 'Não foi possível revogar.' }
Read-Host 'Pressione Enter para fechar'
