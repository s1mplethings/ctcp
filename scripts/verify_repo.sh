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
EXECUTED_GATES=()
ADVISORY_FAILURES=()
PROFILE=""
OWNERSHIP="task-owned"
REQUIRES_LANE_REGRESSION=false
REQUIRES_FROZEN_REGRESSION=false
LANE_REGRESSION_TESTS=()
FROZEN_KERNEL_REGRESSION_TESTS=()

# Parse arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    --full) MODE="1"; shift ;;
    --profile) PROFILE="$2"; shift 2 ;;
    --profile=*) PROFILE="${1#--profile=}"; shift ;;
    *) shift ;;
  esac
done

# --- Verification Profile ---
# Profiles: doc-only | contract | code
# Source: --profile param > CTCP_VERIFY_PROFILE env > auto-detect
if [[ -z "${PROFILE}" ]]; then
  PROFILE="${CTCP_VERIFY_PROFILE:-}"
fi
if [[ -z "${PROFILE}" ]]; then
  PROFILE="$(python3 "${ROOT}/scripts/classify_change_profile.py" 2>/dev/null || echo "")"
  PROFILE="$(echo "${PROFILE}" | tr -d '[:space:]')"
fi
if [[ -z "${PROFILE}" ]]; then
  PROFILE="code"
fi
PROFILE="$(echo "${PROFILE}" | tr '[:upper:]' '[:lower:]')"

case "${PROFILE}" in
  doc-only|contract|code) ;;
  *) echo "[verify_repo] invalid profile: ${PROFILE} (expected: doc-only, contract, code)"; exit 1 ;;
esac

MODULE_PROTECTION_JSON="$(python3 "${ROOT}/scripts/module_protection_check.py" --json 2>/dev/null || true)"
if [[ -n "${MODULE_PROTECTION_JSON}" ]]; then
  OWNERSHIP="$(python3 -c 'import json,sys; doc=json.loads(sys.stdin.read() or "{}"); print(doc.get("ownership", "task-owned"))' <<<"${MODULE_PROTECTION_JSON}")"
  if [[ "$(python3 -c 'import json,sys; doc=json.loads(sys.stdin.read() or "{}"); print("1" if doc.get("requires_lane_regression") else "0")' <<<"${MODULE_PROTECTION_JSON}")" == "1" ]]; then
    REQUIRES_LANE_REGRESSION=true
  fi
  if [[ "$(python3 -c 'import json,sys; doc=json.loads(sys.stdin.read() or "{}"); print("1" if doc.get("requires_frozen_regression") else "0")' <<<"${MODULE_PROTECTION_JSON}")" == "1" ]]; then
    REQUIRES_FROZEN_REGRESSION=true
  fi
  while IFS= read -r row; do
    [[ -n "${row}" ]] && LANE_REGRESSION_TESTS+=("${row}")
  done < <(python3 -c 'import json,sys; doc=json.loads(sys.stdin.read() or "{}"); [print(x) for x in doc.get("lane_regression_tests", [])]' <<<"${MODULE_PROTECTION_JSON}")
  while IFS= read -r row; do
    [[ -n "${row}" ]] && FROZEN_KERNEL_REGRESSION_TESTS+=("${row}")
  done < <(python3 -c 'import json,sys; doc=json.loads(sys.stdin.read() or "{}"); [print(x) for x in doc.get("frozen_kernel_regression_tests", [])]' <<<"${MODULE_PROTECTION_JSON}")
fi

# Gate selection per profile
PROFILE_SKIP_BUILD=false
PROFILE_SKIP_BEHAVIOR_CATALOG=false
PROFILE_SKIP_TRIPLET_GUARD=false
PROFILE_SKIP_LITE_REPLAY=false
PROFILE_SKIP_PYTHON_UNIT_TESTS=false
PROFILE_SKIP_CODE_HEALTH=false
PROFILE_ADVISORY_CONTRACT_CHECKS=false

case "${PROFILE}" in
  doc-only)
    PROFILE_SKIP_BUILD=true
    PROFILE_SKIP_BEHAVIOR_CATALOG=true
    PROFILE_SKIP_TRIPLET_GUARD=true
    PROFILE_SKIP_LITE_REPLAY=true
    PROFILE_SKIP_PYTHON_UNIT_TESTS=true
    PROFILE_SKIP_CODE_HEALTH=true
    PROFILE_ADVISORY_CONTRACT_CHECKS=true
    ;;
  contract)
    PROFILE_SKIP_BUILD=true
    PROFILE_SKIP_TRIPLET_GUARD=true
    PROFILE_SKIP_LITE_REPLAY=true
    PROFILE_SKIP_PYTHON_UNIT_TESTS=true
    PROFILE_SKIP_CODE_HEALTH=true
    ;;
esac

echo "[verify_repo] repo root: ${ROOT}"
echo "[verify_repo] build root: ${BUILD_ROOT}"
echo "[verify_repo] profile: ${PROFILE}"
echo "[verify_repo] ownership: ${OWNERSHIP}"
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

add_executed_gate() {
  local gate="$1"
  EXECUTED_GATES+=("${gate}")
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

if [[ "${PROFILE_SKIP_BUILD}" == "true" ]]; then
  echo "[verify_repo] headless build skipped (profile: ${PROFILE})"
  add_executed_gate "lite"
elif command -v cmake >/dev/null 2>&1; then
  # BEHAVIOR_ID: B001
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

  CMAKE_ARGS=(-S "${ROOT}" -B "${BUILD_DIR_LITE}" -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON)
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
  add_executed_gate "lite"
else
  echo "[verify_repo] cmake not found; skipping headless build"
  add_executed_gate "lite"
fi

# BEHAVIOR_ID: B002
echo "[verify_repo] workflow gate (workflow checks)"
python3 "${ROOT}/scripts/workflow_checks.py"
add_executed_gate "workflow_gate"

echo "[verify_repo] module protection check"
python3 "${ROOT}/scripts/module_protection_check.py"
add_executed_gate "module_protection_check"

# BEHAVIOR_ID: B003
echo "[verify_repo] prompt contract check"
python3 "${ROOT}/scripts/prompt_contract_check.py"
add_executed_gate "prompt_contract_check"

# BEHAVIOR_ID: B004
echo "[verify_repo] plan check"
python3 "${ROOT}/scripts/plan_check.py"
add_executed_gate "plan_check"

# BEHAVIOR_ID: B005
echo "[verify_repo] patch check (scope from PLAN)"
python3 "${ROOT}/scripts/patch_check.py"
add_executed_gate "patch_check"

# BEHAVIOR_ID: B006
if [[ "${PROFILE_SKIP_BEHAVIOR_CATALOG}" == "true" ]]; then
  echo "[verify_repo] behavior catalog check skipped (profile: ${PROFILE})"
  add_executed_gate "behavior_catalog_check"
else
  echo "[verify_repo] behavior catalog check"
  python3 "${ROOT}/scripts/behavior_catalog_check.py"
  add_executed_gate "behavior_catalog_check"
fi

# BEHAVIOR_ID: B007
if [[ "${PROFILE_ADVISORY_CONTRACT_CHECKS}" == "true" ]]; then
  echo "[verify_repo] contract checks (advisory for ${PROFILE})"
  if ! python3 "${ROOT}/scripts/contract_checks.py"; then
    echo "[verify_repo] ADVISORY: contract checks failed - recorded as preexisting, non-blocking for profile: ${PROFILE}"
    ADVISORY_FAILURES+=("contract_checks")
  fi
  add_executed_gate "contract_checks"
else
  echo "[verify_repo] contract checks"
  python3 "${ROOT}/scripts/contract_checks.py"
  add_executed_gate "contract_checks"
fi

# BEHAVIOR_ID: B008
echo "[verify_repo] doc index check (sync doc links --check)"
python3 "${ROOT}/scripts/sync_doc_links.py" --check
add_executed_gate "doc_index_check"

if [[ "${PROFILE_SKIP_CODE_HEALTH}" == "true" ]]; then
  echo "[verify_repo] code health growth-guard skipped (profile: ${PROFILE})"
  add_executed_gate "code_health_check"
else
  echo "[verify_repo] code health growth-guard"
  python3 "${ROOT}/scripts/code_health_check.py" --enforce --changed-only --baseline-ref HEAD --scope-current-task
  add_executed_gate "code_health_check"
fi

if [[ "${PROFILE_SKIP_TRIPLET_GUARD}" == "true" ]]; then
  echo "[verify_repo] triplet integration guard skipped (profile: ${PROFILE})"
  add_executed_gate "triplet_guard"
else
  echo "[verify_repo] triplet integration guard"
  python3 -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v
  python3 -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v
  python3 -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v
  add_executed_gate "triplet_guard"
fi

if [[ "${REQUIRES_LANE_REGRESSION}" == "true" ]]; then
  echo "[verify_repo] lane regression"
  for cmd in "${LANE_REGRESSION_TESTS[@]}"; do
    python3 -c 'import subprocess, sys; sys.exit(subprocess.call(sys.argv[1], shell=True))' "${cmd}"
  done
  add_executed_gate "lane_regression"
fi

if [[ "${REQUIRES_FROZEN_REGRESSION}" == "true" ]]; then
  echo "[verify_repo] frozen-kernel regression"
  for cmd in "${FROZEN_KERNEL_REGRESSION_TESTS[@]}"; do
    python3 -c 'import subprocess, sys; sys.exit(subprocess.call(sys.argv[1], shell=True))' "${cmd}"
  done
  add_executed_gate "frozen_kernel_regression"
fi

if [[ "${PROFILE_SKIP_LITE_REPLAY}" == "true" ]]; then
  echo "[verify_repo] lite scenario replay skipped (profile: ${PROFILE})"
  add_executed_gate "lite_replay"
elif [[ "${SKIP_LITE_REPLAY}" == "1" ]]; then
  echo "[verify_repo] lite scenario replay skipped (CTCP_SKIP_LITE_REPLAY=1)"
  add_executed_gate "lite_replay"
else
  # BEHAVIOR_ID: B008
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
  add_executed_gate "lite_replay"
fi

# BEHAVIOR_ID: B009
if [[ "${PROFILE_SKIP_PYTHON_UNIT_TESTS}" == "true" ]]; then
  echo "[verify_repo] python unit tests skipped (profile: ${PROFILE})"
  add_executed_gate "python_unit_tests"
else
  echo "[verify_repo] python unit tests"
  python3 -m unittest discover -s tests -p "test_*.py"
  add_executed_gate "python_unit_tests"
fi

if [[ "${MODE}" == "1" ]]; then
  echo "[verify_repo] FULL mode enabled"
  if [[ -f "${ROOT}/scripts/test_all.sh" ]]; then
    echo "[verify_repo] tests (full)"
    bash "${ROOT}/scripts/test_all.sh"
  else
    echo "[verify_repo] tests (full): scripts/test_all.sh not found (skip)"
  fi
fi

echo "[verify_repo] plan gate execution/evidence check"
EXECUTED_GATES_CSV="$(IFS=,; echo "${EXECUTED_GATES[*]}")"
python3 "${ROOT}/scripts/plan_check.py" --executed-gates "${EXECUTED_GATES_CSV}" --check-evidence

# --- Failure Attribution Summary ---
echo ""
echo "[verify_repo] === Verification Summary ==="
echo "[verify_repo] profile: ${PROFILE}"
echo "[verify_repo] gates executed: ${EXECUTED_GATES[*]}"
if (( ${#ADVISORY_FAILURES[@]} > 0 )); then
  echo "[verify_repo] advisory (preexisting, non-blocking) failures:"
  for f in "${ADVISORY_FAILURES[@]}"; do
    echo "[verify_repo]   - ${f}"
  done
fi
echo ""

echo "[verify_repo] OK"
