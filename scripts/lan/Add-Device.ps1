param([string]$Name)
$ErrorActionPreference = 'Stop'
$dataRoot = Join-Path $env:LOCALAPPDATA 'LocalAuthor\lan'
$runtime = Get-Content -LiteralPath (Join-Path $dataRoot 'runtime.json') -Raw | ConvertFrom-Json
if (-not $Name) { $Name = Read-Host 'Nome do computador que vai conectar' }
if (-not $Name.Trim()) { throw 'Informe um nome.' }
$outputDir = Join-Path $dataRoot 'connections'; New-Item -ItemType Directory -Force -Path $outputDir | Out-Null
$connectionFile = Join-Path $outputDir (([Guid]::NewGuid().ToString('N'))+'.localauthor')
& $runtime.Gateway add-device --data $dataRoot --name $Name --output $connectionFile
if ($LASTEXITCODE -ne 0) { throw 'Não foi possível criar a conexão.' }
Write-Host 'Transfira somente este arquivo para seu outro computador. Ele concede acesso ao seu workspace.'
Read-Host 'Pressione Enter para fechar'
