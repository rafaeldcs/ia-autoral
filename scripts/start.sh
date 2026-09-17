#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PYTHON="${PYTHON:-python3}"
if [ -x "$ROOT/.venv/bin/python" ]; then PYTHON="$ROOT/.venv/bin/python"; fi
export PYTHONPATH="$ROOT/src"
export PYTHONUTF8=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
"$PYTHON" -c 'import sys; assert sys.version_info >= (3,11), "Python 3.11+ necessario"'
"$PYTHON" -m localauthor init
printf '\nToken local (nao compartilhe):\n'
"$PYTHON" -m localauthor token
exec "$PYTHON" -m localauthor serve
