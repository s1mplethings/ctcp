#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ART_ROOT="${ROOT}/artifacts/verify"
LATEST_PTR="${ART_ROOT}/latest_proof_path.txt"
OLD_PROOF=""

if [[ -f "${LATEST_PTR}" ]]; then
  old_dir="$(cat "${LATEST_PTR}" | tr -d '\r\n')"
  if [[ -n "${old_dir}" && -f "${old_dir}/proof.json" ]]; then
    OLD_PROOF="${old_dir}/proof.json"
  fi
fi

SMOKE_PREFIX="${VERIFY_SMOKE_PREFIX:-}"
if [[ -z "${SMOKE_PREFIX}" && "$(uname -s)" == "Linux" ]]; then
  if command -v xvfb-run >/dev/null 2>&1; then
    SMOKE_PREFIX="xvfb-run -a"
  fi
fi

cmd=(
  python3 tools/run_verify.py
  --src "${ROOT}"
  --build "${ROOT}/build_verify"
  --install-prefix "${ROOT}/dist"
  --artifacts-root "${ROOT}/artifacts/verify"
  --config "Release"
)

if [[ -n "${VERIFY_SMOKE_CMD:-}" ]]; then
  cmd+=(--smoke-cmd "${VERIFY_SMOKE_CMD}")
fi
if [[ -n "${SMOKE_PREFIX}" ]]; then
  cmd+=(--smoke-prefix "${SMOKE_PREFIX}")
fi
if [[ -n "${VERIFY_CMAKE_ARGS:-}" ]]; then
  IFS=';' read -r -a parts <<< "${VERIFY_CMAKE_ARGS}"
  for p in "${parts[@]}"; do
    [[ -z "${p}" ]] && continue
    cmd+=(--cmake-arg "${p}")
  done
fi
if [[ -n "${VERIFY_CTEST_ARGS:-}" ]]; then
  IFS=';' read -r -a parts <<< "${VERIFY_CTEST_ARGS}"
  for p in "${parts[@]}"; do
    [[ -z "${p}" ]] && continue
    cmd+=(--ctest-arg "${p}")
  done
fi

echo "[verify] run_verify start"
set +e
"${cmd[@]}"
run_rc=$?
set -e
echo "[verify] run_verify rc=${run_rc}"

if [[ ! -f "${LATEST_PTR}" ]]; then
  echo "[verify][error] latest proof pointer missing: ${LATEST_PTR}" >&2
  exit 3
fi
PROOF_DIR="$(cat "${LATEST_PTR}" | tr -d '\r\n')"
if [[ -z "${PROOF_DIR}" ]]; then
  echo "[verify][error] empty proof dir pointer" >&2
  exit 4
fi
NEW_PROOF="${PROOF_DIR}/proof.json"

echo "[verify] gate check on ${PROOF_DIR}"
set +e
python3 tools/adlc_gate.py --proof-dir "${PROOF_DIR}"
gate_rc=$?
set -e
echo "[verify] adlc_gate rc=${gate_rc}"

if [[ -n "${OLD_PROOF}" && -f "${OLD_PROOF}" && -f "${NEW_PROOF}" && "${OLD_PROOF}" != "${NEW_PROOF}" ]]; then
  contrast_out="${PROOF_DIR}/contrast_report.md"
  echo "[verify] writing contrast report: ${contrast_out}"
  python3 tools/contrast_proof.py --old "${OLD_PROOF}" --new "${NEW_PROOF}" --out "${contrast_out}"
fi

if [[ ${gate_rc} -ne 0 ]]; then
  exit ${gate_rc}
fi
exit 0
