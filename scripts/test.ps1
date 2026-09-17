param([switch]$AllowUnavailableSymlinks)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$env:PYTHONUTF8 = "1"
$env:OPENBLAS_NUM_THREADS = "1"
$env:OMP_NUM_THREADS = "1"
$TestArgs = @("scripts/run-tests.py")
if ($AllowUnavailableSymlinks) { $TestArgs += "--allow-unavailable-symlinks" }
if (Test-Path ".venv\Scripts\python.exe") {
    & ".venv\Scripts\python.exe" @TestArgs
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3 @TestArgs
} else { & python @TestArgs }
if ($LASTEXITCODE -ne 0) { throw "Ha testes com falha; consulte reports/test-results.json." }
