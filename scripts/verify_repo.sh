#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="${ROOT}/build"

echo "[verify_repo] repo root: ${ROOT}"

find_qt6_config_dir() {
  if [[ -n "${Qt6_DIR:-}" && -f "${Qt6_DIR}/Qt6Config.cmake" ]]; then
    echo "${Qt6_DIR}"
    return 0
  fi

  if [[ -n "${CMAKE_PREFIX_PATH:-}" ]]; then
    IFS=':' read -r -a prefixes <<< "${CMAKE_PREFIX_PATH}"
    for p in "${prefixes[@]}"; do
      [[ -z "${p}" ]] && continue
      for c in "${p}" "${p}/lib/cmake/Qt6" "${p}/cmake/Qt6"; do
        if [[ -f "${c}/Qt6Config.cmake" ]]; then
          echo "${c}"
          return 0
        fi
      done
    done
  fi

  if command -v qmake >/dev/null 2>&1; then
    qt_prefix="$(qmake -query QT_INSTALL_PREFIX 2>/dev/null || true)"
    for c in "${qt_prefix}/lib/cmake/Qt6" "${qt_prefix}/cmake/Qt6"; do
      if [[ -f "${c}/Qt6Config.cmake" ]]; then
        echo "${c}"
        return 0
      fi
    done
  fi
  return 1
}

# 1) Build (best-effort)
if command -v cmake >/dev/null 2>&1; then
  if QT6_CONFIG_DIR="$(find_qt6_config_dir)"; then
    echo "[verify_repo] Qt6 config detected: ${QT6_CONFIG_DIR}"
    echo "[verify_repo] cmake configure..."
    cmake -S "${ROOT}" -B "${BUILD_DIR}" -DCMAKE_BUILD_TYPE=Release -DCMAKE_PREFIX_PATH="${QT6_CONFIG_DIR}"
    echo "[verify_repo] cmake build..."
    cmake --build "${BUILD_DIR}" --config Release

    if [ -f "${BUILD_DIR}/CTestTestfile.cmake" ] && command -v ctest >/dev/null 2>&1; then
      echo "[verify_repo] ctest..."
      ctest --test-dir "${BUILD_DIR}" --output-on-failure
    else
      echo "[verify_repo] no tests detected (skipping ctest)"
    fi
  else
    echo "[verify_repo] Qt6 SDK not found; skipping C++ build"
  fi
else
  echo "[verify_repo] cmake not found; skipping C++ build"
fi

# 2) Web build (best-effort)
if [ -f "${ROOT}/web/package.json" ]; then
  echo "[verify_repo] web/package.json detected"
  if command -v npm >/dev/null 2>&1; then
    pushd "${ROOT}/web" >/dev/null
    if [ -f package-lock.json ]; then npm ci; else npm install; fi
    if node -e "const p=require('./package.json'); process.exit(p.scripts && p.scripts.build ? 0 : 1)"; then
      npm run build
    else
      echo "[verify_repo] no npm build script (skipping)"
    fi
    popd >/dev/null
  else
    echo "[verify_repo] npm not found; skipping web build"
  fi
else
  echo "[verify_repo] no web frontend detected (web/package.json missing)"
fi

# 3) Workflow checks (hard)
echo "[verify_repo] workflow gate (workflow checks)"
python3 "${ROOT}/scripts/workflow_checks.py"

# 4) Contract checks (hard)
echo "[verify_repo] contract checks"
python3 "${ROOT}/scripts/contract_checks.py"

# 5) Sync doc links (hard)
echo "[verify_repo] doc index check (sync doc links --check)"
python3 "${ROOT}/scripts/sync_doc_links.py" --check

# 6) Tests (optional but recommended)
if [ -f "${ROOT}/scripts/test_all.sh" ]; then
  echo "[verify_repo] tests"
  bash "${ROOT}/scripts/test_all.sh"
else
  echo "[verify_repo] tests: scripts/test_all.sh not found (skip)"
fi

echo "[verify_repo] OK"
