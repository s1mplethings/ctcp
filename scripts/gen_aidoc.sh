#!/usr/bin/env bash
# gen_aidoc.sh — 生成 AI Doc 骨架
# 用法： bash scripts/gen_aidoc.sh /path/to/project
set -euo pipefail
if [ $# -lt 1 ]; then
  echo "Usage: $0 <target-dir>"; exit 1
fi
SCRIPT_DIR=$(cd -- "$(dirname "$0")" && pwd)
REPO_ROOT=$(cd -- "${SCRIPT_DIR}/.." && pwd)
TPL1="${REPO_ROOT}/ai_context/templates/aidoc"
TPL2="${REPO_ROOT}/ai_context/ai_context/templates/aidoc"
TPL="$TPL1"
if [ ! -d "$TPL" ]; then
  TPL="$TPL2"
fi
if [ ! -d "$TPL" ]; then
  echo "Template not found: $TPL1 OR $TPL2" >&2
  exit 1
fi
DST="$1/docs/aidoc"
mkdir -p "$DST"
for f in "$TPL"/*; do
  base=$(basename "$f")
  if [ -f "$DST/$base" ]; then cp "$DST/$base" "$DST/$base.bak"; fi
  cp "$f" "$DST/$base"
done
echo "[gen_aidoc] copied to $DST"
