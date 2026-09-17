$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot)
# Run build-lan.ps1 first. The older fixture contains the same updater code with a lower version.
& dotnet publish dotnet/LocalAuthor.Client/LocalAuthor.Client.csproj -c Release -r win-x64 --self-contained true -p:PublishSingleFile=true -p:IncludeNativeLibrariesForSelfExtract=true -p:Version=0.2.99 -o build/update-fixture --nologo
if ($LASTEXITCODE -ne 0) { throw 'Falha ao construir cliente anterior de teste.' }
& dotnet publish dotnet/LocalAuthor.UpdateFailureFixture/LocalAuthor.UpdateFailureFixture.csproj -c Release -r win-x64 --self-contained true -p:PublishSingleFile=true -p:IncludeNativeLibrariesForSelfExtract=true -o build/update-failure --nologo
if ($LASTEXITCODE -ne 0) { throw 'Falha ao construir simulador de erro.' }
& .venv/Scripts/python.exe scripts/client-update-smoke.py
if ($LASTEXITCODE -ne 0) { throw 'Testes de atualizacao falharam.' }
