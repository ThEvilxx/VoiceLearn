#!/usr/bin/env bash
# 一键去掉所有 .draft 后缀，激活 AI 配置文件。
# 用法: bash activate_drafts.sh [项目根目录]
set -euo pipefail

ROOT="${1:-.}"
cd "$ROOT"

count=0
while IFS= read -r -d '' draft; do
  target="${draft%.draft}"
  if [ -e "$target" ]; then
    echo "⚠ 跳过 ${draft}（${target} 已存在，不覆盖）"
  else
    mv "$draft" "$target"
    echo "✅ ${draft} → ${target}"
    ((count++))
  fi
done < <(find . -name "*.draft" -print0)

if [ "$count" -eq 0 ]; then
  echo "没有找到 .draft 文件。"
else
  echo ""
  echo "共激活 ${count} 个文件。"
fi
