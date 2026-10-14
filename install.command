#!/bin/bash
# Xcode 中文语言包 · 安装器
# 每次运行自动检测：Xcode 路径变化 / Xcode 版本更新 / 翻译表更新 —— 变化即自动重新生成计划
# 三层机制：主包中文声明 + xcplugindata 标题直写 + strings en 表直写（动态菜单运行时查表）
cd "$(dirname "$0")" || exit 1
BASE="$(pwd)"
source "$BASE/config.sh"

# Xcode 路径有效性检查
if [ ! -d "$XCODE_APP" ]; then
  echo "!! 未找到 Xcode: $XCODE_APP"
  echo "   请编辑本目录下 config.sh 中的 XCODE_APP 为你的 Xcode 实际安装路径后重试"
  read -r -p "按回车键关闭…"
  exit 1
fi
echo "使用 Xcode: $XCODE_APP"

# ── 计划新鲜度检测（每次双击都执行）──
MARKER="$BASE/stage/.xcode-marker"
CUR_VER=$(defaults read "$XCODE_APP/Contents/version.plist" ProductBuildVersion 2>/dev/null)
SAVED_APP=""; SAVED_VER=""
if [ -f "$MARKER" ]; then
  SAVED_APP=$(sed -n '1p' "$MARKER")
  SAVED_VER=$(sed -n '2p' "$MARKER")
fi

REGEN=""
if [ ! -f "$BASE/stage/plan-pd.tsv" ]; then
  REGEN="首次使用（无安装计划）"
elif [ "$SAVED_APP" != "$XCODE_APP" ]; then
  REGEN="Xcode 路径已变化（$SAVED_APP → $XCODE_APP）"
elif [ -n "$CUR_VER" ] && [ "$SAVED_VER" != "$CUR_VER" ]; then
  REGEN="Xcode 已更新（$SAVED_VER → $CUR_VER）"
  rm -rf "$BASE/backup-pd" "$BASE/backup-en-strings"
  echo "（Xcode 已更新，重置备份目录）"
elif [ -n "$(find "$BASE/translations" "$BASE/assets" -name '*.json' -newer "$BASE/stage/plan-pd.tsv" 2>/dev/null | head -1)" ]; then
  REGEN="翻译表有更新"
fi

if [ -n "$REGEN" ]; then
  echo "== $REGEN，重新生成安装计划 =="
  python3 "$BASE/apply_plugindata.py" || { echo "!! 生成失败"; read -r -p "按回车键关闭…"; exit 1; }
fi

echo "== 步骤 1/4：安装主包中文声明 =="
mkdir -p "$XCODE_APP/Contents/Resources/zh_CN.lproj"
cp "$BASE/assets/appbundle_zh/zh_CN.lproj/InfoPlist.strings" "$XCODE_APP/Contents/Resources/zh_CN.lproj/"
echo "→ $XCODE_APP/Contents/Resources/zh_CN.lproj"

echo "== 步骤 2/4：写入翻译版 xcplugindata（静态菜单/命令标题）=="
mkdir -p "$BASE/backup-pd"
touch "$BASE/backup-pd/plan.tsv"
while IFS=$'\t' read -r src dst; do
  if ! grep -qF "$dst" "$BASE/backup-pd/plan.tsv"; then
    n=$(wc -l < "$BASE/backup-pd/plan.tsv")
    n=$((n+1))
    cp "$dst" "$BASE/backup-pd/$n.xcplugindata" || echo "  !! 备份失败: $dst"
    printf 'backup-pd/%s.xcplugindata\t%s\n' "$n" "$dst" >> "$BASE/backup-pd/plan.tsv"
  fi
done < "$BASE/stage/plan-pd.tsv"
sort -u "$BASE/stage/plan-pd.tsv" | while IFS=$'\t' read -r src dst; do
  echo "→ $dst"
  cp "$BASE/$src" "$dst" || echo "  !! 失败: $dst"
done

echo "== 步骤 3/4：写入翻译版 strings en 表（动态菜单运行时查表）=="
if [ -f "$BASE/stage/plan-en-strings.tsv" ]; then
  mkdir -p "$BASE/backup-en-strings"
  touch "$BASE/backup-en-strings/plan.tsv"
  while IFS=$'\t' read -r src dst; do
    if ! grep -qF "$dst" "$BASE/backup-en-strings/plan.tsv"; then
      n=$(wc -l < "$BASE/backup-en-strings/plan.tsv")
      n=$((n+1))
      if [ -f "$dst" ]; then
        cp "$dst" "$BASE/backup-en-strings/$n.strings" || echo "  !! 备份失败: $dst"
        printf 'backup-en-strings/%s.strings\t%s\n' "$n" "$dst" >> "$BASE/backup-en-strings/plan.tsv"
      else
        printf 'NEW\t%s\n' "$dst" >> "$BASE/backup-en-strings/plan.tsv"
      fi
    fi
  done < "$BASE/stage/plan-en-strings.tsv"
  sort -u "$BASE/stage/plan-en-strings.tsv" | while IFS=$'\t' read -r src dst; do
    echo "→ $dst"
    cp "$BASE/$src" "$dst" || echo "  !! 失败: $dst"
  done
else
  echo "（无 strings 计划，跳过）"
fi

echo "== 步骤 4/4：清理旧版 zh_CN strings 残留（如有）=="
if [ -f "$BASE/stage/plan-strings.tsv" ]; then
  sort -u "$BASE/stage/plan-strings.tsv" | while IFS=$'\t' read -r src dst; do
    [ -d "$dst" ] && rm -rf "$dst" && echo "→ 清理 $dst"
  done
fi

echo ""
echo "== 安装完成 =="
echo "请完全退出 Xcode（Cmd+Q）后重新打开。"
echo "回滚恢复英文：双击 remove.command"
read -r -p "按回车键关闭…" _
