#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_ROOT="${CTCP_BUILD_ROOT:-${ROOT}}"
mkdir -p "${BUILD_ROOT}"
BUILD_DIR_LITE="${BUILD_ROOT}/build_lite"
CTEST_EXE=""
MODE="${CTCP_FULL_GATE:-0}"
WRITE_FIXTURES="${CTCP_WRITE_FIXTURES:-0}"
SKIP_LITE_REPLAY="${CTCP_SKIP_LITE_REPLAY:-0}"
USE_NINJA="${CTCP_USE_NINJA:-0}"
BUILD_PARALLEL="${CTCP_BUILD_PARALLEL:-}"
COMPILER_LAUNCHER="${CTCP_COMPILER_LAUNCHER:-}"
if [[ "${1:-}" == "--full" ]]; then
  MODE="1"
fi

echo "[verify_repo] repo root: ${ROOT}"
echo "[verify_repo] build root: ${BUILD_ROOT}"
if [[ "${MODE}" == "1" ]]; then
  echo "[verify_repo] mode: FULL"
else
echo "[verify_repo] mode: LITE"
fi
echo "[verify_repo] write_fixtures: ${WRITE_FIXTURES}"
BUILD_ARTIFACTS_COMMITTED_MESSAGE="$(printf '\u6784\u5efa\u4ea7\u7269\u88ab\u63d0\u4ea4\u4e86\uff0c\u8bf7\u4ece git \u4e2d\u79fb\u9664\u5e76\u66f4\u65b0 .gitignore')"
RUN_ARTIFACTS_COMMITTED_MESSAGE="Run outputs exist or are tracked inside repo; move them to external CTCP_RUNS_ROOT."
PY_SHIM_DIR=""

cleanup_python_alias() {
  if [[ -n "${PY_SHIM_DIR}" && -d "${PY_SHIM_DIR}" ]]; then
    rm -rf "${PY_SHIM_DIR}"
  fi
}

trap cleanup_python_alias EXIT

ensure_python_alias() {
  if command -v python >/dev/null 2>&1; then
    return
  fi
  if ! command -v python3 >/dev/null 2>&1; then
    return
  fi
  PY_SHIM_DIR="$(mktemp -d)"
  ln -s "$(command -v python3)" "${PY_SHIM_DIR}/python"
  export PATH="${PY_SHIM_DIR}:${PATH}"
  echo "[verify_repo] python shim enabled: python -> python3"
}

anti_pollution_gate() {
  echo "[verify_repo] anti-pollution gate (build/run artifacts)"
  local tracked_files=()
  mapfile -t tracked_files < <(git -C "${ROOT}" ls-files)
  local tracked_build=()
  local tracked_runs=()
  local path=""
  for path in "${tracked_files[@]}"; do
    if [[ "${path}" == build*/* ]]; then
      tracked_build+=("${path}")
    fi
    if [[ "${path}" == simlab/_runs*/* || "${path}" == meta/runs/* ]]; then
      tracked_runs+=("${path}")
    fi
  done

  if (( ${#tracked_build[@]} > 0 )); then
    echo "[verify_repo] tracked build artifacts detected (showing up to 20):"
    local i=0
    for path in "${tracked_build[@]}"; do
      echo "  ${path}"
      ((i += 1))
      if (( i >= 20 )); then
        break
      fi
    done
    echo "[verify_repo] ${BUILD_ARTIFACTS_COMMITTED_MESSAGE}"
    echo "[verify_repo] suggested cleanup commands:"
    echo "  git rm -r --cached build_lite build_verify"
    echo '  git commit -m "Stop tracking build outputs"'
    exit 1
  fi
  if (( ${#tracked_runs[@]} > 0 )); then
    echo "[verify_repo] tracked run outputs detected (showing up to 20):"
    local r=0
    for path in "${tracked_runs[@]}"; do
      echo "  ${path}"
      ((r += 1))
      if (( r >= 20 )); then
        break
      fi
    done
    echo "[verify_repo] ${RUN_ARTIFACTS_COMMITTED_MESSAGE}"
    exit 1
  fi

  local unignored_build=()
  while IFS= read -r path; do
    if [[ -n "${path}" ]]; then
      unignored_build+=("${path}")
    fi
  done < <(git -C "${ROOT}" ls-files --others --exclude-standard -- 'build*/**')
  if (( ${#unignored_build[@]} > 0 )); then
    echo "[verify_repo] unignored build outputs detected (showing up to 20)."
    local j=0
    for path in "${unignored_build[@]}"; do
      echo "  ${path}"
      ((j += 1))
      if (( j >= 20 )); then
        break
      fi
    done
    echo "[verify_repo] Build outputs appear inside repo; clean them or update ignore rules."
    exit 1
  fi

  local unignored_runs=()
  while IFS= read -r path; do
    if [[ -n "${path}" ]]; then
      unignored_runs+=("${path}")
    fi
  done < <(git -C "${ROOT}" ls-files --others --exclude-standard -- 'simlab/_runs*/**' 'meta/runs/**')
  if (( ${#unignored_runs[@]} > 0 )); then
    echo "[verify_repo] unignored run outputs detected (showing up to 20)."
    local k=0
    for path in "${unignored_runs[@]}"; do
      echo "  ${path}"
      ((k += 1))
      if (( k >= 20 )); then
        break
      fi
    done
    echo "[verify_repo] ${RUN_ARTIFACTS_COMMITTED_MESSAGE}"
    exit 1
  fi
}

anti_pollution_gate
ensure_python_alias

if command -v cmake >/dev/null 2>&1; then
  CMAKE_EXE="$(command -v cmake)"
  if [[ -z "${BUILD_PARALLEL}" ]]; then
    if command -v nproc >/dev/null 2>&1; then
      BUILD_PARALLEL="$(nproc)"
    else
      BUILD_PARALLEL="4"
    fi
  fi
  if [[ -z "${COMPILER_LAUNCHER}" ]]; then
    if command -v ccache >/dev/null 2>&1; then
      COMPILER_LAUNCHER="ccache"
    elif command -v sccache >/dev/null 2>&1; then
      COMPILER_LAUNCHER="sccache"
    fi
  fi
  if command -v ctest >/dev/null 2>&1; then
    CTEST_EXE="$(command -v ctest)"
  elif [[ -x "$(dirname "${CMAKE_EXE}")/ctest" ]]; then
    CTEST_EXE="$(dirname "${CMAKE_EXE}")/ctest"
  fi
  echo "[verify_repo] build parallel: ${BUILD_PARALLEL}"
  if [[ "${USE_NINJA}" == "1" ]]; then
    echo "[verify_repo] generator: Ninja"
  fi
  if [[ -n "${COMPILER_LAUNCHER}" ]]; then
    echo "[verify_repo] compiler launcher: ${COMPILER_LAUNCHER}"
  else
    echo "[verify_repo] compiler launcher: none"
  fi

  CMAKE_ARGS=(-S "${ROOT}" -B "${BUILD_DIR_LITE}" -DCMAKE_BUILD_TYPE=Release -DCTCP_ENABLE_GUI=OFF -DBUILD_TESTING=ON)
  if [[ "${USE_NINJA}" == "1" ]]; then
    CMAKE_ARGS=(-G Ninja "${CMAKE_ARGS[@]}")
  fi
  if [[ -n "${COMPILER_LAUNCHER}" ]]; then
    CMAKE_ARGS+=("-DCMAKE_CXX_COMPILER_LAUNCHER=${COMPILER_LAUNCHER}")
  fi
  echo "[verify_repo] cmake configure (headless lite)"
  cmake "${CMAKE_ARGS[@]}"
  echo "[verify_repo] cmake build (headless lite)"
  cmake --build "${BUILD_DIR_LITE}" --config Release --parallel "${BUILD_PARALLEL}"
  if [[ -f "${BUILD_DIR_LITE}/CTestTestfile.cmake" ]] && [[ -n "${CTEST_EXE}" ]]; then
    echo "[verify_repo] ctest lite"
    "${CTEST_EXE}" --test-dir "${BUILD_DIR_LITE}" --output-on-failure -R "headless_smoke|verify_tools_selftest" -j "${BUILD_PARALLEL}"
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

if [[ "${SKIP_LITE_REPLAY}" == "1" ]]; then
  echo "[verify_repo] lite scenario replay skipped (CTCP_SKIP_LITE_REPLAY=1)"
else
  echo "[verify_repo] lite scenario replay"
  if [[ "${WRITE_FIXTURES}" == "1" ]]; then
    RUNS_ROOT="${ROOT}/tests/fixtures/adlc_forge_full_bundle/runs/simlab_lite_runs"
    SUMMARY_OUT="${ROOT}/tests/fixtures/adlc_forge_full_bundle/runs/_simlab_lite_summary.json"
    python3 "${ROOT}/simlab/run.py" \
      --suite lite \
      --runs-root "${RUNS_ROOT}" \
      --json-out "${SUMMARY_OUT}"
  else
    python3 "${ROOT}/simlab/run.py" --suite lite
  fi
fi

echo "[verify_repo] python unit tests"
python3 -m unittest discover -s tests -p "test_*.py"

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
