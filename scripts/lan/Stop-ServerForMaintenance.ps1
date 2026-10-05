param(
    [Parameter(Mandatory=$true)][int]$BackendPid,
    [Parameter(Mandatory=$true)][int]$SupervisorPid,
    [Parameter(Mandatory=$true)][string]$Report,
    [switch]$CheckOnly
)
$ErrorActionPreference = 'Stop'
if (-not [IO.Path]::IsPathRooted($Report) -or (Test-Path -LiteralPath $Report)) { throw 'Use a new absolute private report path.' }
# This operator tool never terminates the database-owning backend forcibly.
# Run it as a separate hidden PowerShell process, not in an interactive console.
$dataRoot = Join-Path $env:LOCALAPPDATA 'LocalAuthor\lan'
$runtime = Get-Content -LiteralPath (Join-Path $dataRoot 'runtime.json') -Raw | ConvertFrom-Json
$config = Get-Content -LiteralPath (Join-Path $dataRoot 'server.json') -Raw | ConvertFrom-Json
$record = @{schema=1; check_only=[bool]$CheckOnly; backend_pid=$BackendPid; supervisor_pid=$SupervisorPid; status='pending'}
$supervisorStopped = $false
$attached = $false
try {
    $backend = Get-CimInstance Win32_Process -Filter "ProcessId=$BackendPid"
    $supervisor = Get-CimInstance Win32_Process -Filter "ProcessId=$SupervisorPid"
    if (-not $backend -or $backend.Name -ne 'python.exe' -or $backend.CommandLine -notmatch '\-m localauthor .* serve(\s|$)' -or
        $backend.CommandLine -notlike ('*'+$config.BackendHome+'*')) { throw 'Backend identity was not verified.' }
    if (-not $supervisor -or $supervisor.CommandLine -notmatch 'Start-Server\.ps1.*-Supervise') { throw 'Supervisor identity was not verified.' }
    $headers = @{Authorization='Bearer '+(Get-Content -LiteralPath (Join-Path $config.BackendHome 'api.token') -Raw).Trim()}
    $jobs = Invoke-RestMethod -Uri ('http://127.0.0.1:'+$config.BackendPort+'/api/jobs') -Headers $headers -TimeoutSec 8
    if (@($jobs | Where-Object { $_.state -in @('running','queued') }).Count -ne 0) { throw 'Finish or cancel queued/running work before maintenance.' }
    $headers.Clear()
    Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class LocalAuthorMaintenanceConsole {
 [DllImport("kernel32.dll",SetLastError=true)] public static extern bool FreeConsole();
 [DllImport("kernel32.dll",SetLastError=true)] public static extern bool AttachConsole(uint pid);
 [DllImport("kernel32.dll",SetLastError=true)] public static extern uint GetConsoleProcessList(uint[] ids,uint count);
 [DllImport("kernel32.dll",SetLastError=true)] public static extern bool SetConsoleCtrlHandler(IntPtr handler,bool add);
 [DllImport("kernel32.dll",SetLastError=true)] public static extern bool GenerateConsoleCtrlEvent(uint type,uint group);
}
'@
    [LocalAuthorMaintenanceConsole]::FreeConsole() | Out-Null
    if (-not [LocalAuthorMaintenanceConsole]::AttachConsole([uint32]$BackendPid)) { throw ('Cannot attach backend console: '+[Runtime.InteropServices.Marshal]::GetLastWin32Error()) }
    $attached = $true
    $consoleIds = New-Object uint32[] 32
    $count = [LocalAuthorMaintenanceConsole]::GetConsoleProcessList($consoleIds,32)
    if ($count -lt 1 -or $count -gt 32) { throw 'Console inventory unavailable or excessive.' }
    $members = @($consoleIds[0..($count-1)])
    $allowed = @([uint32]$PID,[uint32]$BackendPid,[uint32]$backend.ParentProcessId)
    if (@($members | Where-Object { $_ -notin $allowed }).Count -ne 0 -or [uint32]$BackendPid -notin $members) { throw 'Shared console contains another process; no signal sent.' }
    $record.console_members = $members
    if ($CheckOnly) { $record.status='check-passed-no-process-stopped' }
    else {
        # Supervisor writes no application DB. Recheck identity before stopping
        # this relaunch loop; backend receives normal Ctrl+C / KeyboardInterrupt.
        if ((Get-CimInstance Win32_Process -Filter "ProcessId=$SupervisorPid").CommandLine -ne $supervisor.CommandLine) { throw 'Supervisor changed.' }
        Stop-Process -Id $SupervisorPid -ErrorAction Stop
        $supervisorStopped = $true
        if (-not [LocalAuthorMaintenanceConsole]::SetConsoleCtrlHandler([IntPtr]::Zero,$true)) { throw 'Cannot protect maintenance helper.' }
        if (-not [LocalAuthorMaintenanceConsole]::GenerateConsoleCtrlEvent(0,0)) { throw 'Ctrl+C signal failed.' }
        Start-Sleep -Milliseconds 500
        [LocalAuthorMaintenanceConsole]::FreeConsole() | Out-Null
        $attached = $false
        $deadline = (Get-Date).AddSeconds(45)
        while ((Get-Process -Id $BackendPid -ErrorAction SilentlyContinue) -and (Get-Date) -lt $deadline) { Start-Sleep -Milliseconds 500 }
        if ((Get-Process -Id $BackendPid -ErrorAction SilentlyContinue) -or (Test-Path -LiteralPath (Join-Path $config.BackendHome 'server.lock'))) {
            throw 'Backend did not complete normal shutdown; no forced termination or lock removal.'
        }
        $record.status='stopped-cooperatively'
        $record.supervisor_restart_required=$true
    }
} catch {
    $record.status='blocked'
    $record.error=$_.Exception.Message
    if ($supervisorStopped) {
        Start-Process -FilePath 'powershell.exe' -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-File',('"'+(Join-Path $env:LOCALAPPDATA 'LocalAuthor\lan-runtime\Start-Server.ps1')+'"'),'-Supervise') -WindowStyle Hidden | Out-Null
        $record.supervisor_restarted=$true
    }
} finally {
    if ($attached) { [LocalAuthorMaintenanceConsole]::FreeConsole() | Out-Null }
    $record | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $Report -Encoding UTF8
}
if ($record.status -eq 'blocked') { exit 2 }
