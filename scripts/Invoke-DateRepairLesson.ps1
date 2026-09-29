param(
    [Parameter(Mandatory=$true)][string]$Project,
    [Parameter(Mandatory=$true)][string]$Revision,
    [Parameter(Mandatory=$true)][string]$BaselineCheckpoint,
    [string]$Image = 'localauthor-code-repair-lab:1'
)
$ErrorActionPreference = 'Stop'
$lessonRepository = Split-Path $PSScriptRoot -Parent
$lessonProject = (Resolve-Path -LiteralPath $Project).Path
$lessonCheckpoint = (Resolve-Path -LiteralPath $BaselineCheckpoint).Path
if ((Split-Path $lessonCheckpoint -Leaf) -ne 'best-validation.npz') { throw 'Use the reviewed baseline checkpoint.' }
$lessonId = 'date-repair-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + [guid]::NewGuid().ToString('N').Substring(0,8)
$lessonModel = Join-Path $env:LOCALAPPDATA ('LocalAuthor/models/' + $lessonId)
$lessonEvidence = Join-Path $lessonRepository ('reports/' + $lessonId)
New-Item -ItemType Directory -Path $lessonModel,$lessonEvidence | Out-Null
$lessonArchive = Join-Path $lessonEvidence 'baseline.tar'
git -C $lessonProject archive --format=tar "--output=$lessonArchive" $Revision
if ($LASTEXITCODE -ne 0) { throw 'Unable to archive the requested Git revision.' }
$lessonImageId = docker image inspect $Image --format '{{.Id}}'
if ($LASTEXITCODE -ne 0) { throw 'Reviewed lab image is unavailable. No host fallback.' }

function Invoke-LessonSandbox {
    param([string]$Stage,[string[]]$Mounts,[string[]]$Command)
    $lessonContainer = $lessonId + '-' + $Stage
    $lessonArgs = @('create','--name',$lessonContainer,'--network','none','--read-only',
        '--cap-drop','ALL','--security-opt','no-new-privileges','--user','10001:10001',
        '--memory','2g','--cpus','2','--pids-limit','128','--tmpfs','/tmp:rw,nosuid,size=768m',
        '-e','OPENBLAS_NUM_THREADS=1','-e','PYTHONDONTWRITEBYTECODE=1')
    foreach ($mount in $Mounts) { $lessonArgs += @('--mount',$mount) }
    $lessonArgs += @($lessonImageId) + $Command
    $lessonContainerId = docker @lessonArgs
    if ($LASTEXITCODE -ne 0) { throw 'Unable to create sandbox.' }
    $lessonInspection = (docker inspect $lessonContainerId | ConvertFrom-Json)[0]
    $lessonHost = $lessonInspection.HostConfig
    if ($lessonHost.NetworkMode -ne 'none' -or !$lessonHost.ReadonlyRootfs -or
        $lessonInspection.Config.User -ne '10001:10001' -or $lessonHost.CapDrop -notcontains 'ALL' -or
        $lessonHost.SecurityOpt -notcontains 'no-new-privileges' -or
        $lessonHost.PidsLimit -ne 128 -or $lessonHost.Memory -ne 2147483648 -or
        $lessonInspection.Mounts.Count -ne $Mounts.Count) { throw 'Sandbox verification failed; container was not started.' }
    $lessonReceipt = @{ image=$lessonImageId; network=$lessonHost.NetworkMode; readOnly=$lessonHost.ReadonlyRootfs;
        user=$lessonInspection.Config.User; capabilitiesDropped=$lessonHost.CapDrop; securityOptions=$lessonHost.SecurityOpt;
        memory=$lessonHost.Memory; pids=$lessonHost.PidsLimit; container=$lessonContainerId }
    $lessonReceipt | ConvertTo-Json | Set-Content -Encoding utf8 (Join-Path $lessonEvidence ($Stage + '-sandbox.json'))
    try {
        docker start -a $lessonContainerId 2>&1 | Tee-Object -FilePath (Join-Path $lessonEvidence ($Stage + '.log'))
        $lessonState = (docker inspect $lessonContainerId | ConvertFrom-Json)[0].State
        if ($lessonState.Running -or $lessonState.ExitCode -ne 0) { throw "Stage $Stage failed. Preserved evidence: $lessonEvidence" }
    } finally {
        # Only this created container; private model and receipts are retained.
        $lessonState = (docker inspect $lessonContainerId | ConvertFrom-Json)[0].State
        if (!$lessonState.Running) { docker rm $lessonContainerId | Out-Null }
    }
}
$lessonCommon = @("type=bind,source=$lessonRepository,target=/workspace,readonly")
Invoke-LessonSandbox -Stage 'train' -Mounts ($lessonCommon + @(
    "type=bind,source=$lessonModel,target=/models/$lessonId",
    "type=bind,source=$(Split-Path $lessonCheckpoint -Parent),target=/baseline,readonly")) -Command @(
    '/workspace/scripts/train-date-repair.py','--output',"/models/$lessonId",'--baseline','/baseline/best-validation.npz')
Invoke-LessonSandbox -Stage 'evaluate' -Mounts ($lessonCommon + @(
    "type=bind,source=$lessonModel,target=/models/$lessonId,readonly",
    "type=bind,source=$lessonArchive,target=/baseline.tar,readonly",
    "type=bind,source=$lessonEvidence,target=/evidence")) -Command @(
    '/workspace/scripts/qualify-date-repair.py','--model',"/models/$lessonId",'--archive','/baseline.tar','--output','/evidence/evaluation')
Write-Output "Lesson finished; review $lessonEvidence/evaluation. No model activated and no project files changed."
