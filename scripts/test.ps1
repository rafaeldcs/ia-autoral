$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$env:PYTHONUTF8 = "1"
$env:OPENBLAS_NUM_THREADS = "1"
$env:OMP_NUM_THREADS = "1"
if (Test-Path ".venv\Scripts\python.exe") {
    & ".venv\Scripts\python.exe" scripts/run-tests.py
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3 scripts/run-tests.py
} else { & python scripts/run-tests.py }
if ($LASTEXITCODE -ne 0) { throw "Ha testes com falha; consulte reports/test-results.json." }
