#!/usr/bin/env bash
# CTCP 智能自动提交脚本 (Unix 版)
# 版本格式: X.Y.Z
#   X = 重大原理/架构改动
#   Y = 正常原理修改
#   Z = 日常修缮/修复
#
# 用法:
#   ./scripts/auto_commit.sh                     # 自动检测
#   ./scripts/auto_commit.sh -l patch            # 强制 patch
#   ./scripts/auto_commit.sh -l minor -m "msg"   # 指定级别+描述
#   ./scripts/auto_commit.sh -d                  # 仅预览
#   ./scripts/auto_commit.sh -n                  # 不推送

set -euo pipefail

LEVEL=""
NO_PUSH=false
DRY_RUN=false
USER_MSG=""

while getopts "l:m:nd" opt; do
  case $opt in
    l) LEVEL="$OPTARG" ;;
    m) USER_MSG="$OPTARG" ;;
    n) NO_PUSH=true ;;
    d) DRY_RUN=true ;;
    *) echo "用法: $0 [-l major|minor|patch] [-m message] [-n] [-d]"; exit 1 ;;
  esac
done

REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || { echo "不在 git 仓库内"; exit 1; })
cd "$REPO_ROOT"

# ── 隐私守卫 ──
PRIVACY_PATTERNS=(
  '\.key$' '\.pem$' '\.p12$' '\.pfx$' '\.secret$'
  '\.credentials$' '\.token$' '_token\.txt$'
  'api_key' 'id_rsa' '\.netrc$' '\.npmrc$' '\.pypirc$'
  '/secrets/' '/private/' '/\.agent_private/' '/\.env'
)

is_private() {
  local f="$1"
  for p in "${PRIVACY_PATTERNS[@]}"; do
    if echo "$f" | grep -qE "$p"; then return 0; fi
  done
  return 1
}

# ── 检查改动 ──
STATUS=$(git status --porcelain 2>&1)
if [ -z "$STATUS" ]; then
  echo "[auto_commit] 没有任何改动，跳过。"
  exit 0
fi

# ── 收集文件 ──
CHANGED=()
BLOCKED=()
while IFS= read -r line; do
  [ -z "$line" ] && continue
  fpath="${line:3}"
  fpath="${fpath## }"
  # rename
  if [[ "$fpath" == *" -> "* ]]; then fpath="${fpath##* -> }"; fi
  fpath="${fpath//\"/}"

  if is_private "$fpath"; then
    BLOCKED+=("$fpath")
  else
    CHANGED+=("$fpath")
  fi
done <<< "$STATUS"

if [ ${#BLOCKED[@]} -gt 0 ]; then
  echo "[auto_commit] 隐私守卫拦截:"
  printf "  BLOCKED: %s\n" "${BLOCKED[@]}"
fi

if [ ${#CHANGED[@]} -eq 0 ]; then
  echo "[auto_commit] 过滤后无可提交文件。"
  exit 0
fi

# ── 自动检测级别 ──
# major is NEVER auto-detected. Use -l major explicitly for true architectural redesign.
detect_level() {
  local has_minor=false

  for f in "${CHANGED[@]}"; do
    case "$f" in
      # Core architecture docs => minor (not major)
      CMakeLists.txt|AGENTS.md|docs/00_CORE.md|docs/01_north_star.md|ai_context/00_AI_CONTRACT.md)
        has_minor=true ;;
      # Executable code => minor
      src/*|include/*|executor/*|frontend/*|contracts/*|ctcp/*)
        has_minor=true ;;
      scripts/*.py)
        has_minor=true ;;
      *.cpp|*.h)
        has_minor=true ;;
      *.py)
        has_minor=true ;;
    esac
  done

  if $has_minor; then echo "minor"
  else echo "patch"
  fi
}

if [ -z "$LEVEL" ]; then
  LEVEL=$(detect_level)
  echo "[auto_commit] 自动检测级别: $LEVEL"
else
  echo "[auto_commit] 手动指定级别: $LEVEL"
fi

# ── 版本号 ──
VERSION_FILE="$REPO_ROOT/VERSION"
if [ -f "$VERSION_FILE" ]; then
  CURRENT=$(cat "$VERSION_FILE" | tr -d '[:space:]')
else
  CURRENT="0.0.0"
fi

IFS='.' read -r V_MAJ V_MIN V_PAT <<< "$CURRENT"

case "$LEVEL" in
  major) V_MAJ=$((V_MAJ + 1)); V_MIN=0; V_PAT=0 ;;
  minor) V_MIN=$((V_MIN + 1)); V_PAT=0 ;;
  patch) V_PAT=$((V_PAT + 1)) ;;
esac
NEW_VER="$V_MAJ.$V_MIN.$V_PAT"

# ── 生成日志 ──
generate_summary() {
  declare -A groups
  for f in "${CHANGED[@]}"; do
    dir="${f%%/*}"
    [[ "$f" != */* ]] && dir="root"
    groups[$dir]=$(( ${groups[$dir]:-0} + 1 ))
  done
  # 排序取前3
  sorted=$(for k in "${!groups[@]}"; do echo "${groups[$k]} $k"; done | sort -rn | head -3)
  parts=""
  while IFS= read -r line; do
    [ -z "$line" ] && continue
    cnt="${line%% *}"; d="${line#* }"
    parts="${parts:+$parts, }${d}(${cnt})"
  done <<< "$sorted"

  case "$LEVEL" in
    major) prefix="重大" ;;
    minor) prefix="改进" ;;
    patch) prefix="修缮" ;;
  esac
  echo "$prefix: $parts"
}

AUTO_SUMMARY=$(generate_summary)
COMMIT_MSG="$NEW_VER $AUTO_SUMMARY"
[ -n "$USER_MSG" ] && COMMIT_MSG="$NEW_VER $AUTO_SUMMARY — $USER_MSG"

# ── 预览 ──
echo ""
echo "╔══════════════════════════════════════════╗"
echo "║  CTCP Auto Commit                        ║"
echo "╚══════════════════════════════════════════╝"
echo "  版本: $CURRENT → $NEW_VER"
echo "  级别: $LEVEL"
echo "  日志: $COMMIT_MSG"
echo "  文件数: ${#CHANGED[@]}"
echo ""
printf "    + %s\n" "${CHANGED[@]}"
echo ""

if $DRY_RUN; then
  echo "[auto_commit] DryRun 模式，不实际提交。"
  exit 0
fi

# ── 提交 ──
printf "%s\n" "$NEW_VER" > "$VERSION_FILE"

for f in "${CHANGED[@]}"; do
  git add "$f" 2>/dev/null || true
done
git add VERSION 2>/dev/null || true

for f in "${BLOCKED[@]}"; do
  git reset HEAD "$f" 2>/dev/null || true
done

git commit -m "$COMMIT_MSG"
echo "[auto_commit] ✓ 提交成功: $COMMIT_MSG"

# ── 推送 ──
if ! $NO_PUSH; then
  BRANCH=$(git branch --show-current 2>/dev/null)
  if [ -n "$BRANCH" ]; then
    echo "[auto_commit] 推送到 origin/$BRANCH ..."
    if git push origin "$BRANCH" 2>&1; then
      echo "[auto_commit] ✓ 推送成功"
    else
      echo "[auto_commit] ✗ 推送失败（提交已保存在本地）"
    fi
  fi
else
  echo "[auto_commit] NoPush 标记，跳过推送。"
fi

echo "[auto_commit] 完成。"
