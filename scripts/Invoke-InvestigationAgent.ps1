param(
    [Parameter(Mandatory=$true)][string]$Project,
    [Parameter(Mandatory=$true)][string]$Report,
    [string]$Revision = 'HEAD'
)
$ErrorActionPreference = 'Stop'
$agentRepository = Split-Path $PSScriptRoot -Parent
$agentHome = Join-Path $env:LOCALAPPDATA 'LocalAuthor'
$agentCertificate = Get-Content -Raw (Join-Path $agentHome 'exports/investigation-agent-qualification.json') | ConvertFrom-Json
if ($agentCertificate.scope -ne 'missing-date-investigation-tools-v2' -or $agentCertificate.state -ne 'qualified_scoped') { throw 'No qualified investigation agent is activated.' }
$agentModels = (Resolve-Path -LiteralPath (Join-Path $agentHome 'models')).Path
function Resolve-AgentModel {
    param([string]$Relative)
    if ([IO.Path]::IsPathRooted($Relative) -or $Relative.Contains('..')) { throw 'Invalid model path.' }
    $resolved = (Resolve-Path -LiteralPath (Join-Path $agentModels $Relative)).Path
    if (!$resolved.StartsWith($agentModels + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { throw 'Model escaped private storage.' }
    return Split-Path $resolved -Parent
}
$agentPolicy = Resolve-AgentModel $agentCertificate.checkpoint
$agentRepair = Resolve-AgentModel $agentCertificate.repairCheckpoint
$agentProject = (Resolve-Path -LiteralPath $Project).Path
$agentId = 'investigation-' + [guid]::NewGuid().ToString('N')
$agentEvidence = Join-Path $agentRepository ('reports/' + $agentId)
New-Item -ItemType Directory -Path $agentEvidence | Out-Null
@{report=$Report} | ConvertTo-Json | Set-Content -Encoding utf8 (Join-Path $agentEvidence 'request.json')
git -C $agentProject archive --format=tar "--output=$(Join-Path $agentEvidence 'baseline.tar')" $Revision
if ($LASTEXITCODE -ne 0) { throw 'Git snapshot failed; no code executed.' }
$agentImage = docker image inspect localauthor-code-repair-lab:1 --format '{{.Id}}'
if ($LASTEXITCODE -ne 0) { throw 'Reviewed Docker image unavailable; no host fallback.' }
$agentContainer = docker create --name $agentId --network none --read-only --cap-drop ALL --security-opt no-new-privileges --user 10001:10001 --memory 2g --cpus 2 --pids-limit 128 --tmpfs /tmp:rw,nosuid,size=512m -e OPENBLAS_NUM_THREADS=1 -e PYTHONDONTWRITEBYTECODE=1 --mount "type=bind,source=$agentRepository,target=/workspace,readonly" --mount "type=bind,source=$agentPolicy,target=/models/$(Split-Path $agentPolicy -Leaf),readonly" --mount "type=bind,source=$agentRepair,target=/models/$(Split-Path $agentRepair -Leaf),readonly" --mount "type=bind,source=$agentEvidence,target=/evidence" $agentImage /workspace/scripts/run-investigation-agent.py --model "/models/$(Split-Path $agentPolicy -Leaf)" --repair-model "/models/$(Split-Path $agentRepair -Leaf)" --archive /evidence/baseline.tar --request /evidence/request.json --output /evidence/result
if ($LASTEXITCODE -ne 0) { throw 'Sandbox creation failed.' }
$agentInspect = (docker inspect $agentContainer | ConvertFrom-Json)[0]
$agentHost = $agentInspect.HostConfig
if ($agentHost.NetworkMode -ne 'none' -or !$agentHost.ReadonlyRootfs -or $agentHost.CapDrop -notcontains 'ALL' -or
    $agentHost.SecurityOpt -notcontains 'no-new-privileges' -or $agentInspect.Config.User -ne '10001:10001' -or
    $agentHost.Memory -ne 2147483648 -or $agentHost.PidsLimit -ne 128 -or $agentInspect.Mounts.Count -ne 4) { throw 'Sandbox verification failed; container was not started.' }
@{image=$agentImage;network=$agentHost.NetworkMode;readOnly=$agentHost.ReadonlyRootfs;user=$agentInspect.Config.User;capDrop=$agentHost.CapDrop;security=$agentHost.SecurityOpt;memory=$agentHost.Memory;pids=$agentHost.PidsLimit} | ConvertTo-Json | Set-Content -Encoding utf8 (Join-Path $agentEvidence 'sandbox.json')
try {
    docker start -a $agentContainer 2>&1 | Tee-Object -FilePath (Join-Path $agentEvidence 'execution.log')
    $agentState = (docker inspect $agentContainer | ConvertFrom-Json)[0].State
    if ($agentState.ExitCode -notin @(0,2)) { throw "Execution failed; preserved evidence: $agentEvidence" }
    Write-Output "Review $agentEvidence/result. Original project files were not changed."
} finally {
    $agentState = (docker inspect $agentContainer | ConvertFrom-Json)[0].State
    if (!$agentState.Running) { docker rm $agentContainer | Out-Null }
}
