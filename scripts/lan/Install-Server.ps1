param([Parameter(Mandatory=$true)][string]$BindAddress,[string]$SourceRoot)
$ErrorActionPreference = 'Stop'
if (-not $SourceRoot) { $SourceRoot = Split-Path (Split-Path $PSScriptRoot) }
$SourceRoot = [IO.Path]::GetFullPath($SourceRoot)
$address = Get-NetIPAddress -AddressFamily IPv4 -IPAddress $BindAddress -ErrorAction Stop
$dataRoot = Join-Path $env:LOCALAPPDATA 'LocalAuthor\lan'
$runtimeRoot = Join-Path $env:LOCALAPPDATA 'LocalAuthor\lan-runtime'
New-Item -ItemType Directory -Force -Path $dataRoot,$runtimeRoot | Out-Null
$sid = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
& icacls $dataRoot '/inheritance:r' '/grant:r' ('*'+$sid+':(OI)(CI)F') '*S-1-5-18:(OI)(CI)F' | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Não foi possível proteger os dados de acesso.' }
Copy-Item -LiteralPath (Join-Path $SourceRoot 'build\lan-server\LocalAuthor.Lan.exe') -Destination $runtimeRoot
foreach ($file in 'Start-Server.ps1','Enable-Firewall.ps1','Add-Device.ps1','Revoke-Device.ps1') { Copy-Item -LiteralPath (Join-Path $PSScriptRoot $file) -Destination $runtimeRoot }
$gateway = Join-Path $runtimeRoot 'LocalAuthor.Lan.exe'
$python = Join-Path $SourceRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) { throw 'Ambiente Python do servidor não encontrado.' }
$runtime = @{SourceRoot=$SourceRoot;Python=$python;Gateway=$gateway}
$runtime | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $dataRoot 'runtime.json') -Encoding UTF8
if (-not (Test-Path -LiteralPath (Join-Path $dataRoot 'server.json'))) {
    & $gateway init --data $dataRoot --home (Join-Path $env:LOCALAPPDATA 'LocalAuthor') --bind $BindAddress --prefix $address.PrefixLength
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao configurar HTTPS.' }
}
$startup = Join-Path $runtimeRoot 'Start-Server.ps1'
$command = 'powershell.exe -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "'+$startup+'" -Supervise'
New-Item -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run' -Force | Out-Null
Set-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run' -Name LocalAuthorLan -Value $command
$delivery = Join-Path ([Environment]::GetFolderPath('Desktop')) 'LocalAuthor-Rede'
New-Item -ItemType Directory -Force -Path $delivery | Out-Null
$shell = New-Object -ComObject WScript.Shell
foreach ($item in @(@('Iniciar servidor','Start-Server.ps1'),@('Criar conexão','Add-Device.ps1'),@('Revogar conexão','Revoke-Device.ps1'))) {
    $shortcut = $shell.CreateShortcut((Join-Path $delivery ($item[0]+'.lnk')))
    $shortcut.TargetPath = 'powershell.exe'; $shortcut.Arguments = '-NoProfile -ExecutionPolicy Bypass -File "'+(Join-Path $runtimeRoot $item[1])+'"'
    $shortcut.WorkingDirectory = $runtimeRoot; $shortcut.Save()
}
$requestFirewall = @'
$ErrorActionPreference = 'Stop'
$script = Join-Path $PSScriptRoot 'Enable-Firewall.ps1'
Start-Process -FilePath powershell.exe -Verb RunAs -ArgumentList ('-NoProfile -ExecutionPolicy Bypass -File "'+$script+'"')
'@
$requestFirewall | Set-Content -LiteralPath (Join-Path $runtimeRoot 'Request-Firewall.ps1') -Encoding UTF8
$shortcut=$shell.CreateShortcut((Join-Path $delivery 'Liberar rede local (Administrador).lnk'))
$shortcut.TargetPath='powershell.exe';$shortcut.Arguments='-NoProfile -ExecutionPolicy Bypass -File "'+(Join-Path $runtimeRoot 'Request-Firewall.ps1')+'"';$shortcut.Save()
Start-Process -FilePath powershell.exe -ArgumentList @('-NoProfile','-WindowStyle','Hidden','-ExecutionPolicy','Bypass','-File',('"'+$startup+'"'),'-Supervise') -WindowStyle Hidden | Out-Null
Write-Output ('Servidor preparado. Atalhos em: '+$delivery)
Write-Output 'A regra de firewall exige executar Liberar rede local como administrador.'
