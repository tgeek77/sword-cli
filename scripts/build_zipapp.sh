#!/usr/bin/env bash
# Build a single-file zipapp: dist/biblecli (biblecli + pysword).
# Edit packaging here only; application code lives under biblecli/.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STAGE="${ROOT}/.zipapp_stage"
OUT_DIR="${ROOT}/dist"
OUT="${OUT_DIR}/biblecli"

if [[ -n "${PYTHON:-}" ]]; then
  :
elif [[ -x "${ROOT}/.venv/bin/python" ]]; then
  PYTHON="${ROOT}/.venv/bin/python"
else
  PYTHON="python3"
fi

if ! command -v "${PYTHON}" >/dev/null 2>&1; then
  echo "error: ${PYTHON} not found (set PYTHON=... to override)" >&2
  exit 1
fi

if ! "${PYTHON}" -c "import zipapp" 2>/dev/null; then
  echo "error: ${PYTHON} cannot import zipapp (need Python 3.5+)" >&2
  exit 1
fi

echo "Staging into ${STAGE} ..."
rm -rf "${STAGE}"
mkdir -p "${STAGE}" "${OUT_DIR}"

echo "Installing pysword into staging ..."
"${PYTHON}" -m pip install --upgrade --quiet -t "${STAGE}" "pysword>=0.2.8"

echo "Copying biblecli package from this checkout ..."
"${PYTHON}" - <<PY
import shutil
from pathlib import Path

root = Path(${ROOT@Q})
stage = Path(${STAGE@Q})
src = root / "biblecli"
dst = stage / "biblecli"
if dst.exists():
    shutil.rmtree(dst)
shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"))
PY

# Drop pip metadata from the zip to keep the artifact small and tidy.
rm -rf "${STAGE}"/*.dist-info "${STAGE}"/*.egg-info

echo "Writing ${OUT} ..."
"${PYTHON}" -m zipapp "${STAGE}" \
  -m "biblecli.cli:main" \
  -p "/usr/bin/env python3" \
  -o "${OUT}"
chmod +x "${OUT}"

SIZE="$(wc -c < "${OUT}" | tr -d ' ')"
echo "Built ${OUT} (${SIZE} bytes)"
echo "Try: ${OUT} --help"
