#!/bin/bash
# Xcode 中文语言包 · 回滚器（完整恢复英文）
cd "$(dirname "$0")" || exit 1
BASE="$(pwd)"
source "$BASE/config.sh"

echo "== 还原原始 xcplugindata =="
if [ -f "$BASE/backup-pd/plan.tsv" ]; then
  while IFS=$'\t' read -r bak dst; do
    case "$bak" in /*) B="$bak" ;; *) B="$BASE/$bak" ;; esac
    echo "→ $dst"
    cp "$B" "$dst" || echo "  !! 失败: $dst"
  done < "$BASE/backup-pd/plan.tsv"
else
  echo "没有备份记录，跳过"
fi

echo "== 还原原始 strings en 表 =="
if [ -f "$BASE/backup-en-strings/plan.tsv" ]; then
  while IFS=$'\t' read -r bak dst; do
    case "$bak" in /*) B="$bak" ;; *) B="$BASE/$bak" ;; esac
    echo "→ $dst"
    cp "$B" "$dst" || echo "  !! 失败: $dst"
  done < "$BASE/backup-en-strings/plan.tsv"
fi

echo "== 清理 zh_CN strings 残留（如有）=="
if [ -f "$BASE/stage/plan-strings.tsv" ]; then
  sort -u "$BASE/stage/plan-strings.tsv" | while IFS=$'\t' read -r src dst; do
    [ -d "$dst" ] && rm -rf "$dst" && echo "→ $dst"
  done
fi
# 主包运行时键表是我们新建的文件，原包不存在——直接删除即恢复原状（en+zh_CN 双写）
rm -f "$XCODE_APP/Contents/Resources/en.lproj/Localizable.strings"
rm -f "$XCODE_APP/Contents/Resources/zh_CN.lproj/Localizable.strings"
echo "→ 已移除主包运行时键表（如有）"

echo "== 移除主包 zh_CN 声明 =="
rm -rf "$XCODE_APP/Contents/Resources/zh_CN.lproj"
echo "== 已回滚，完全退出 Xcode 后重新打开即恢复英文 =="
read -r -p "按回车键关闭…" _
