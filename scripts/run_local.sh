#!/usr/bin/env bash
# Run the news digest pipeline locally.
# Usage:
#   ./scripts/run_local.sh            # full run, writes to output/
#   ./scripts/run_local.sh --dry-run  # print digest to stdout only
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${PROJECT_ROOT}"

VENV_DIR="${PROJECT_ROOT}/.venv"

# ── Create / sync virtual environment ────────────────────────────────────────
if command -v uv &>/dev/null; then
    echo "Using uv to create/sync venv …"
    uv venv --quiet "${VENV_DIR}" 2>/dev/null || true
    uv pip install --quiet -r requirements.txt --python "${VENV_DIR}/bin/python"
else
    if [[ ! -d "${VENV_DIR}" ]]; then
        echo "Creating virtual environment at ${VENV_DIR} …"
        python3 -m venv "${VENV_DIR}"
    fi
    echo "Installing / updating dependencies …"
    "${VENV_DIR}/bin/pip" install --quiet --upgrade pip
    "${VENV_DIR}/bin/pip" install --quiet -r requirements.txt
fi

# ── Load .env if present ──────────────────────────────────────────────────────
if [[ -f "${PROJECT_ROOT}/.env" ]]; then
    echo "Loading .env …"
    set -a
    # shellcheck disable=SC1091
    source "${PROJECT_ROOT}/.env"
    set +a
fi

# ── Run ───────────────────────────────────────────────────────────────────────
echo "Starting digest pipeline …"
"${VENV_DIR}/bin/python" -m src.main "$@"
