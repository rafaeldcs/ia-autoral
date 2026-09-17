#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
OWNER="${1:-rafaeldcs}"; REPO="${2:-ia-local-autoral}"
[[ "$OWNER" =~ ^[a-zA-Z0-9][a-zA-Z0-9-]{0,38}$ && "$REPO" =~ ^[a-zA-Z0-9._-]+$ ]] || { echo 'Nome invalido.' >&2; exit 1; }
TARGET="$OWNER/$REPO"
if [ "${3:-}" = "--dry-run" ]; then
  printf 'Destino privado proposto: %s\ngh repo create %s --private --source=. --remote=origin --push\n' "$TARGET" "$TARGET"
  exit 0
fi
command -v git >/dev/null; command -v gh >/dev/null
gh auth status --hostname github.com
LOGIN="$(gh api user --jq .login)"
[ "$LOGIN" = "$OWNER" ] || { echo 'Conta autenticada difere do owner; nada publicado.' >&2; exit 1; }
if gh repo view "$TARGET" --json nameWithOwner >/dev/null 2>&1; then echo 'Repositorio existente; nenhum overwrite permitido.' >&2; exit 1; fi
[ -d .git ] || git init -b main
if git remote | grep -qx origin; then echo 'Remote origin existente; revise manualmente.' >&2; exit 1; fi
git config user.name >/dev/null; git config user.email >/dev/null
git add -- .gitignore .gitattributes .github README.md AGENTS.md SECURITY.md CHANGELOG.md THIRD_PARTY_NOTICES.md pyproject.toml requirements-training.txt settings.example.json src ui tests scripts docs dotnet native experiments examples reports
if git diff --cached --name-only | grep -E '(^|/)(api\.token|\.env[^/]*|server\.lock)$|\.(npz|npy|sqlite3|db|pt|pth|safetensors)$'; then echo 'Dados privados no indice: publicacao bloqueada.' >&2; exit 1; fi
if ! git diff --cached --quiet; then git commit -m 'feat: local knowledge platform and experimental authorial CPU model'; fi
git rev-parse --verify HEAD >/dev/null
# No tokens are read or passed explicitly; use the local gh credential flow.
gh repo create "$TARGET" --private --source=. --remote=origin --push --description 'Plataforma local e modelo autoral CPU experimental, sem APIs de IA.'
[ "$(gh repo view "$TARGET" --json isPrivate --jq .isPrivate)" = true ] || { echo 'Visibilidade privada nao confirmada; verifique o repositorio.' >&2; exit 1; }
printf 'Publicado: https://github.com/%s\n' "$TARGET"
