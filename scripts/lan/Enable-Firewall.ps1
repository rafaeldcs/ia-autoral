$ErrorActionPreference = 'Stop'
$principal = [Security.Principal.WindowsPrincipal]::new([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'Execute este arquivo como administrador no servidor.' }
$dataRoot = Join-Path $env:LOCALAPPDATA 'LocalAuthor\lan'
$config = Get-Content -LiteralPath (Join-Path $dataRoot 'server.json') -Raw | ConvertFrom-Json
$runtime = Get-Content -LiteralPath (Join-Path $dataRoot 'runtime.json') -Raw | ConvertFrom-Json
$address = Get-NetIPAddress -AddressFamily IPv4 -IPAddress $config.Bind -ErrorAction Stop
if ($address.PrefixLength -ne $config.Prefix) { throw 'Prefixo de rede mudou. Revise a configuração.' }
if (-not (Test-Path -LiteralPath $runtime.Gateway)) { throw 'Executável do servidor não encontrado.' }
$ruleName = 'LocalAuthor-LAN-HTTPS'
Get-NetFirewallRule -Name $ruleName -ErrorAction SilentlyContinue | Remove-NetFirewallRule
New-NetFirewallRule -Name $ruleName -DisplayName 'LocalAuthor HTTPS - somente rede local' -Direction Inbound -Action Allow -Protocol TCP -LocalPort $config.Port -LocalAddress $config.Bind -RemoteAddress ($config.Bind+'/'+$config.Prefix) -Program $runtime.Gateway -InterfaceAlias $address.InterfaceAlias -Profile Any -EdgeTraversalPolicy Block | Out-Null
Write-Host ('Rede liberada apenas para '+$config.Bind+':'+$config.Port+' e dispositivos da mesma sub-rede.')
Read-Host 'Pressione Enter para fechar'
