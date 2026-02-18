#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR_LITE="${ROOT}/build_lite"
CTEST_EXE=""
MODE="${CTCP_FULL_GATE:-0}"
if [[ "${1:-}" == "--full" ]]; then
  MODE="1"
fi

echo "[verify_repo] repo root: ${ROOT}"
if [[ "${MODE}" == "1" ]]; then
  echo "[verify_repo] mode: FULL"
else
  echo "[verify_repo] mode: LITE"
fi

if command -v cmake >/dev/null 2>&1; then
  CMAKE_EXE="$(command -v cmake)"
  if command -v ctest >/dev/null 2>&1; then
    CTEST_EXE="$(command -v ctest)"
  elif [[ -x "$(dirname "${CMAKE_EXE}")/ctest" ]]; then
    CTEST_EXE="$(dirname "${CMAKE_EXE}")/ctest"
  fi
  echo "[verify_repo] cmake configure (headless lite)"
  cmake -S "${ROOT}" -B "${BUILD_DIR_LITE}" -DCMAKE_BUILD_TYPE=Release -DCTCP_ENABLE_GUI=OFF -DBUILD_TESTING=ON
  echo "[verify_repo] cmake build (headless lite)"
  cmake --build "${BUILD_DIR_LITE}" --config Release
  if [[ -f "${BUILD_DIR_LITE}/CTestTestfile.cmake" ]] && [[ -n "${CTEST_EXE}" ]]; then
    echo "[verify_repo] ctest lite"
    "${CTEST_EXE}" --test-dir "${BUILD_DIR_LITE}" --output-on-failure -R "headless_smoke|verify_tools_selftest"
  else
    echo "[verify_repo] no tests detected or ctest missing in lite build (skip ctest)"
  fi
else
  echo "[verify_repo] cmake not found; skipping headless build"
fi

echo "[verify_repo] workflow gate (workflow checks)"
python3 "${ROOT}/scripts/workflow_checks.py"

echo "[verify_repo] contract checks"
python3 "${ROOT}/scripts/contract_checks.py"

echo "[verify_repo] doc index check (sync doc links --check)"
python3 "${ROOT}/scripts/sync_doc_links.py" --check

echo "[verify_repo] lite scenario replay"
python3 "${ROOT}/simlab/run.py" \
  --suite lite \
  --runs-root "${ROOT}/tests/fixtures/adlc_forge_full_bundle/runs/simlab_lite_runs" \
  --json-out "${ROOT}/tests/fixtures/adlc_forge_full_bundle/runs/_simlab_lite_summary.json"

if [[ "${MODE}" == "1" ]]; then
  echo "[verify_repo] FULL mode enabled"
  if [[ -f "${ROOT}/scripts/test_all.sh" ]]; then
    echo "[verify_repo] tests (full)"
    bash "${ROOT}/scripts/test_all.sh"
  else
    echo "[verify_repo] tests (full): scripts/test_all.sh not found (skip)"
  fi
fi

echo "[verify_repo] OK"
