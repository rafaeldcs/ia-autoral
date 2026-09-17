param(
    [switch]$AllowUnavailableSymlinks,
    [ValidateSet('msedge', 'chrome')][string]$BrowserChannel = 'msedge'
)
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Root '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $Python)) { throw 'Crie .venv e instale requirements-training.txt e requirements-dev.txt antes da validacao.' }
$env:PYTHONUTF8 = '1'
$env:PYTHONPATH = Join-Path $Root 'src'
$env:DOTNET_CLI_TELEMETRY_OPTOUT = '1'
$env:DOTNET_CLI_WORKLOAD_UPDATE_NOTIFY_DISABLE = 'true'
$Checks = [System.Collections.Generic.List[object]]::new()
function Invoke-Validation {
    param([string]$Name, [string]$Executable, [string[]]$Arguments)
    Write-Host "Validando: $Name"
    & $Executable @Arguments
    $Code = $LASTEXITCODE
    $Checks.Add([ordered]@{ name = $Name; exit_code = $Code; success = ($Code -eq 0) })
}
Push-Location $Root
try {
    $TestArgs = @('scripts/run-tests.py', '--report', 'reports/test-results-windows.json')
    if ($AllowUnavailableSymlinks) { $TestArgs += '--allow-unavailable-symlinks' }
    Invoke-Validation 'python-suite' $Python $TestArgs
    Invoke-Validation 'hardware' $Python @('-c', 'import json; from pathlib import Path; from localauthor.diagnostics import diagnose; Path("reports/hardware-windows.json").write_text(json.dumps(diagnose(Path.cwd()),indent=2),encoding="utf-8")')
    Invoke-Validation 'dotnet-host-build' 'dotnet' @('build', 'dotnet/LocalAI.Host/LocalAI.Host.csproj', '-c', 'Release', '--nologo')
    Invoke-Validation 'dotnet-laboratory-build' 'dotnet' @('build', 'examples/laboratory/Laboratory.csproj', '-c', 'Release', '--nologo')
    if (($Checks | Where-Object { $_.name -eq 'dotnet-host-build' }).success) {
        Invoke-Validation 'dotnet-runtime' $Python @('scripts/dotnet-smoke.py', '--report', 'reports/dotnet-smoke-windows.json')
    }
    Invoke-Validation 'browser-ui' $Python @('scripts/ui-smoke.py', '--browser-channel', $BrowserChannel, '--report', 'reports/ui-smoke-windows.json')
    Invoke-Validation 'neural-numerical-smoke' $Python @('scripts/neural-smoke.py', '--report', 'reports/neural-smoke-windows.json')
    $Suite = Get-Content -LiteralPath 'reports/test-results-windows.json' -Raw | ConvertFrom-Json
    $Success = @($Checks | Where-Object { -not $_.success }).Count -eq 0
    [ordered]@{
        at = [DateTime]::UtcNow.ToString('o')
        success = $Success
        complete_python_coverage = $Suite.complete
        checks = $Checks.ToArray()
        limitations = @('Nao audita Docker, CUDA, ACLs ou bloqueio de rede no sistema operacional.', 'Nao qualifica um modelo programador.', 'Nao publica alteracoes no GitHub.')
    } | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath 'reports/windows-validation.json' -Encoding utf8
    if (-not $Success) { throw 'Uma ou mais verificacoes falharam; consulte reports/windows-validation.json.' }
    if (-not $Suite.complete) { Write-Warning 'Validacao parcial: testes de symlink nao executados. Veja allowed_skips no relatorio.' }
} finally { Pop-Location }
