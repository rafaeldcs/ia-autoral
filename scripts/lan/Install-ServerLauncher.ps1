param([Parameter(Mandatory=$true)][string]$Executable)
$ErrorActionPreference = 'Stop'
if (-not (Test-Path -LiteralPath $Executable -PathType Leaf)) { throw 'Aplicativo do servidor não encontrado.' }
$installRoot = Join-Path $env:LOCALAPPDATA 'Programs\LocalAuthorServer'
New-Item -ItemType Directory -Path $installRoot -Force | Out-Null
if ((Get-Item -LiteralPath $installRoot).Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'A pasta de instalação não pode ser um link.' }
$target = Join-Path $installRoot 'LocalAuthor.ServerLauncher.exe'
Copy-Item -LiteralPath $Executable -Destination $target -Force
$desktop = [Environment]::GetFolderPath('Desktop')
$programs = [Environment]::GetFolderPath('Programs')
$delivery = Join-Path $desktop 'LocalAuthor-Rede'
New-Item -ItemType Directory -Path $delivery -Force | Out-Null
$shell = New-Object -ComObject WScript.Shell
foreach ($shortcutPath in @((Join-Path $desktop 'LocalAuthor Servidor.lnk'),(Join-Path $programs 'LocalAuthor Servidor.lnk'),(Join-Path $delivery 'Iniciar servidor.lnk'))) {
    $shortcut = $shell.CreateShortcut($shortcutPath)
    $shortcut.TargetPath = $target
    $shortcut.Arguments = ''
    $shortcut.WorkingDirectory = $installRoot
    $shortcut.Description = 'Liga a IA e o acesso pela rede, com uma janela de status.'
    $shortcut.IconLocation = $target
    $shortcut.Save()
}
Write-Output ('Pronto: '+(Join-Path $desktop 'LocalAuthor Servidor.lnk'))
