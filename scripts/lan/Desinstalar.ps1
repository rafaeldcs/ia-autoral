$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms
$installRoot = [IO.Path]::GetFullPath($PSScriptRoot)
$expectedRoot = [IO.Path]::GetFullPath((Join-Path $env:LOCALAPPDATA 'Programs\LocalAuthorClient'))
if ($installRoot -ne $expectedRoot) { throw 'Pasta de instalação inesperada.' }
if ((Get-Item -LiteralPath $installRoot).Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Pasta não pode ser um link.' }
if ([Windows.Forms.MessageBox]::Show('Remover o aplicativo? Projetos no servidor e conexão pessoal serão preservados.', 'LocalAuthor', 'YesNo', 'Question') -ne 'Yes') { exit }
if (Get-Process -Name LocalAuthor.Client -ErrorAction SilentlyContinue) { [Windows.Forms.MessageBox]::Show('Feche o LocalAuthor antes de desinstalar.'); exit 1 }
$manifest = Get-Content -LiteralPath (Join-Path $installRoot 'payload-manifest.json') -Raw | ConvertFrom-Json
Remove-ItemProperty -LiteralPath 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run' -Name LocalAuthorClient -ErrorAction SilentlyContinue
foreach ($name in $manifest.PSObject.Properties.Name) {
    if ([IO.Path]::GetFileName($name) -ne $name -or $name.Contains(':')) { throw 'Manifesto inválido.' }
    $target = [IO.Path]::GetFullPath((Join-Path $installRoot $name))
    if ([IO.Path]::GetDirectoryName($target) -ne $installRoot) { throw 'Destino fora da instalação.' }
    if (Test-Path -LiteralPath $target) { Remove-Item -LiteralPath $target }
}
Remove-Item -LiteralPath (Join-Path $installRoot 'payload-manifest.json')
if (@(Get-ChildItem -LiteralPath $installRoot -Force).Count -eq 0) { Remove-Item -LiteralPath $installRoot }
$shortcut = Join-Path ([Environment]::GetFolderPath('Programs')) 'LocalAuthor.lnk'
if (Test-Path -LiteralPath $shortcut) { Remove-Item -LiteralPath $shortcut }
Remove-Item -LiteralPath 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\LocalAuthorClient' -ErrorAction SilentlyContinue
[Windows.Forms.MessageBox]::Show('Aplicativo removido. Dados no servidor foram preservados.') | Out-Null
