$ErrorActionPreference = 'Stop'
$sourceRoot = Split-Path (Split-Path $PSScriptRoot)
$dataRoot = Join-Path $env:LOCALAPPDATA 'LocalAuthor\lan'
$runtimeRoot = Join-Path $env:LOCALAPPDATA 'LocalAuthor\lan-runtime'
$runtimePath = Join-Path $dataRoot 'runtime.json'
$configPath = Join-Path $dataRoot 'server.json'
$runtime = Get-Content -LiteralPath $runtimePath -Raw | ConvertFrom-Json
$config = Get-Content -LiteralPath $configPath -Raw | ConvertFrom-Json
$startup = Join-Path $runtimeRoot 'Start-Server.ps1'
$listeners = @(Get-NetTCPConnection -State Listen -LocalPort $config.Port -ErrorAction SilentlyContinue)
$gatewayProcesses = @()
foreach ($listener in $listeners) {
    $process = Get-Process -Id $listener.OwningProcess
    if ($process.Path -ne $runtime.Gateway) { throw 'Porta ocupada por processo diferente do gateway registrado.' }
    $gatewayProcesses += $process
}
$supervisors = @(Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" | Where-Object { $_.CommandLine -like ('*"'+$startup+'"*') -and $_.CommandLine -like '*-Supervise*' })
$versionDir = Join-Path $runtimeRoot ('discovery-'+[Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $versionDir | Out-Null
Copy-Item -LiteralPath (Join-Path $sourceRoot 'build\lan-server\LocalAuthor.Lan.exe') -Destination $versionDir
$backup = Join-Path $dataRoot ('before-discovery-'+[Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $backup | Out-Null
Copy-Item -LiteralPath $runtimePath,$configPath -Destination $backup
foreach ($process in $supervisors) { Stop-Process -Id $process.ProcessId; Wait-Process -Id $process.ProcessId -Timeout 10 -ErrorAction SilentlyContinue }
foreach ($process in ($gatewayProcesses | Sort-Object Id -Unique)) { Stop-Process -Id $process.Id; Wait-Process -Id $process.Id -Timeout 10 -ErrorAction SilentlyContinue }
try {
    $runtime.Gateway = Join-Path $versionDir 'LocalAuthor.Lan.exe'
    $config | Add-Member -NotePropertyName AutoDiscover -NotePropertyValue $true -Force
    $config | Add-Member -NotePropertyName DiscoveryPort -NotePropertyValue 38443 -Force
    $runtime | ConvertTo-Json | Set-Content -LiteralPath $runtimePath -Encoding UTF8
    $config | ConvertTo-Json | Set-Content -LiteralPath $configPath -Encoding UTF8
    foreach ($file in 'Start-Server.ps1','Enable-Firewall.ps1') { Copy-Item -LiteralPath (Join-Path $PSScriptRoot $file) -Destination $runtimeRoot }
    Start-Process -FilePath powershell.exe -ArgumentList @('-NoProfile','-WindowStyle','Hidden','-ExecutionPolicy','Bypass','-File',('"'+$startup+'"'),'-Supervise') -WindowStyle Hidden | Out-Null
    Write-Output 'Descoberta preparada. Reaplique Liberar rede local (Administrador) para atualizar HTTPS e UDP.'
} catch {
    Copy-Item -LiteralPath (Join-Path $backup 'runtime.json') -Destination $runtimePath
    Copy-Item -LiteralPath (Join-Path $backup 'server.json') -Destination $configPath
    Start-Process -FilePath powershell.exe -ArgumentList @('-NoProfile','-WindowStyle','Hidden','-ExecutionPolicy','Bypass','-File',('"'+$startup+'"'),'-Supervise') -WindowStyle Hidden | Out-Null
    throw
}
