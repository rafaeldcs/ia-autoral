$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$env:PYTHONPATH = Join-Path $Root "src"
$env:PYTHONUTF8 = "1"
$env:OPENBLAS_NUM_THREADS = "1"
$env:OMP_NUM_THREADS = "1"
$PythonArgs = @()
if (Test-Path (Join-Path $Root ".venv\Scripts\python.exe")) {
    $Python = Join-Path $Root ".venv\Scripts\python.exe"
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $Python = "py"; $PythonArgs = @("-3")
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $Python = "python"
} else { throw "Python 3.11+ nao encontrado. Instale-o antes de iniciar." }
& $Python @PythonArgs -c "import sys; assert sys.version_info >= (3,11), 'Python 3.11+ necessario'"
if ($LASTEXITCODE -ne 0) { throw "Versao de Python nao suportada." }
& $Python @PythonArgs -m localauthor init
if ($LASTEXITCODE -ne 0) { throw "Falha na inicializacao." }
Write-Host "`nToken local (nao compartilhe):"
& $Python @PythonArgs -m localauthor token
Write-Host "`nAbra http://127.0.0.1:8765 e informe o token acima."
& $Python @PythonArgs -m localauthor serve
if ($LASTEXITCODE -ne 0) { throw "O servidor terminou com erro." }
