param(
    [string]$Owner = "rafaeldcs",
    [string]$Repository = "ia-local-autoral",
    [switch]$DryRun
)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
if ($Owner -notmatch '^[A-Za-z0-9][A-Za-z0-9-]{0,38}$' -or $Repository -notmatch '^[A-Za-z0-9._-]+$') { throw "Owner/repositorio invalido." }
$Target = "$Owner/$Repository"
if ($DryRun) {
    Write-Host "Destino proposto: $Target (PRIVADO)."
    Write-Host "Este modo nao inicializa Git, nao autentica e nao publica."
    Write-Host "Comando de publicacao: gh repo create $Target --private --source=. --remote=origin --push"
    exit 0
}
foreach ($Tool in @("git", "gh")) {
    if (-not (Get-Command $Tool -ErrorAction SilentlyContinue)) { throw "$Tool nao instalado. Instale Git e GitHub CLI antes de publicar." }
}
& gh auth status --hostname github.com
if ($LASTEXITCODE -ne 0) { throw "Autentique localmente com gh auth login. Nao cole token no chat." }
$Login = (& gh api user --jq .login).Trim()
if ($LASTEXITCODE -ne 0 -or $Login -ne $Owner) { throw "A conta autenticada nao corresponde ao owner solicitado. Nenhuma publicacao realizada." }
# Existing remote repositories are NEVER overwritten by this bootstrap script.
& gh repo view $Target --json nameWithOwner 2>$null | Out-Null
if ($LASTEXITCODE -eq 0) { throw "O repositorio $Target ja existe. Este script nao o modifica; escolha outro nome ou revise o destino manualmente." }
if (-not (Test-Path ".git")) {
    & git init -b main
    if ($LASTEXITCODE -ne 0) { throw "git init falhou." }
}
$Remotes = & git remote
if ($Remotes -contains "origin") { throw "Ja existe um remote origin. Revise-o antes de publicar; nao sera substituido." }
$UserName = & git config user.name
$UserEmail = & git config user.email
if (-not $UserName -or -not $UserEmail) { throw "Configure seu user.name e user.email locais no Git antes de criar o commit." }
# Only source directories and reviewed reports are staged; runtime data is never included.
$Allowed = @(".gitignore", ".gitattributes", ".github", "README.md", "AGENTS.md", "SECURITY.md", "CHANGELOG.md", "THIRD_PARTY_NOTICES.md", "pyproject.toml", "requirements-training.txt", "settings.example.json", "src", "ui", "tests", "scripts", "docs", "dotnet", "native", "experiments", "examples", "reports")
& git add -- @Allowed
if ($LASTEXITCODE -ne 0) { throw "git add falhou." }
$Tracked = & git diff --cached --name-only
foreach ($Path in $Tracked) {
    if ($Path -match '(?i)(^|/)(api\.token|\.env[^/]*|server\.lock)$|\.(npz|npy|sqlite3|db|pt|pth|safetensors)$') {
        throw "Arquivo de dados/segredo bloqueado: $Path. Nada foi enviado."
    }
}
& git diff --cached --quiet
if ($LASTEXITCODE -eq 1) {
    & git commit -m "feat: local knowledge platform and experimental authorial CPU model"
    if ($LASTEXITCODE -ne 0) { throw "git commit falhou." }
} elseif ($LASTEXITCODE -ne 0) { throw "Nao foi possivel verificar o indice do Git." }
& git rev-parse --verify HEAD | Out-Null
if ($LASTEXITCODE -ne 0) { throw "Nenhum commit disponivel para publicar." }
& gh repo create $Target --private --source=. --remote=origin --push --description "Plataforma local de conhecimento e revisao de codigo; modelo autoral CPU experimental, sem APIs de IA."
if ($LASTEXITCODE -ne 0) { throw "A publicacao falhou. Confira gh repo view $Target e git remote -v antes de tentar novamente; pode ter havido criacao parcial." }
$Private = & gh repo view $Target --json isPrivate --jq .isPrivate
if ($LASTEXITCODE -ne 0 -or $Private -ne "true") { throw "Nao foi possivel confirmar a visibilidade privada. Verifique o repositorio antes de compartilhar." }
Write-Host "Repositorio privado publicado: https://github.com/$Target"
