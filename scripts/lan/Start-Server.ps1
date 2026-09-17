param([switch]$Supervise)
$ErrorActionPreference = 'Stop'
$dataRoot = Join-Path $env:LOCALAPPDATA 'LocalAuthor\lan'
$runtime = Get-Content -LiteralPath (Join-Path $dataRoot 'runtime.json') -Raw | ConvertFrom-Json
$config = Get-Content -LiteralPath (Join-Path $dataRoot 'server.json') -Raw | ConvertFrom-Json
$mutex = [Threading.Mutex]::new($false, 'Local\LocalAuthorLanSupervisor')
if (-not $mutex.WaitOne(0)) { Write-Output 'Supervisor já está ativo.'; exit }
function Ensure-Servers {
    $backendListener = Get-NetTCPConnection -State Listen -LocalPort $config.BackendPort -ErrorAction SilentlyContinue
    if (-not $backendListener) {
        $lockFile = Join-Path $config.BackendHome 'server.lock'
        if (Test-Path -LiteralPath $lockFile) {
            $lockPid = [int](Get-Content -LiteralPath $lockFile -Raw)
            if (Get-Process -Id $lockPid -ErrorAction SilentlyContinue) { throw 'Processo registrado ainda existe; confira o servidor antes de iniciar outra instância.' }
            Remove-Item -LiteralPath $lockFile
        }
        $env:PYTHONPATH = Join-Path $runtime.SourceRoot 'src'
        $env:PYTHONUTF8 = '1'; $env:OPENBLAS_NUM_THREADS = '1'; $env:OMP_NUM_THREADS = '1'
        Start-Process -FilePath $runtime.Python -ArgumentList @('-m','localauthor','--home',('"'+$config.BackendHome+'"'),'serve','--port',[string]$config.BackendPort) -WorkingDirectory $runtime.SourceRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $dataRoot 'backend.log') -RedirectStandardError (Join-Path $dataRoot 'backend-error.log') | Out-Null
        Start-Sleep -Seconds 3
    }
    $headers = @{Authorization='Bearer '+(Get-Content -LiteralPath (Join-Path $config.BackendHome 'api.token') -Raw).Trim()}
    $health = Invoke-RestMethod -Uri ('http://127.0.0.1:'+$config.BackendPort+'/api/health') -Headers $headers -TimeoutSec 8
    if ($health.status -ne 'ok') { throw 'Backend não está saudável.' }
    $listener = Get-NetTCPConnection -State Listen -LocalPort $config.Port -ErrorAction SilentlyContinue
    if ($listener) {
        $process = Get-Process -Id $listener[0].OwningProcess
        if ($process.Path -ne $runtime.Gateway) { throw 'A porta HTTPS está ocupada por outro programa.' }
    } else {
        Start-Process -FilePath $runtime.Gateway -ArgumentList @('serve','--data',('"'+$dataRoot+'"')) -WindowStyle Hidden -WorkingDirectory (Split-Path $runtime.Gateway) -RedirectStandardOutput (Join-Path $dataRoot 'gateway.log') -RedirectStandardError (Join-Path $dataRoot 'gateway-error.log') | Out-Null
    }
}
try {
    do {
        try { Ensure-Servers } catch { $_.Exception.Message | Set-Content -LiteralPath (Join-Path $dataRoot 'supervisor-error.txt') }
        if ($Supervise) { Start-Sleep -Seconds 30 }
    } while ($Supervise)
} finally { $mutex.ReleaseMutex(); $mutex.Dispose() }
