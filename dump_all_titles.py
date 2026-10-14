#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""提取主包全部 xcplugindata 的 title/overrideTitle，合并去重输出：
1) 已翻译命中的数量 2) 待翻清单（按模块统计）。"""
import json
import plistlib
import re
from pathlib import Path

# 工具目录 = 脚本所在目录（动态，任意位置可用）
TOOL = Path(__file__).resolve().parent
def _read_xcode_app() -> str:
    """从 config.sh 解析 XCODE_APP：跳过 # 注释行，取最后生效行（与 shell source 语义一致）。"""
    for line in reversed((TOOL / "config.sh").read_text(encoding="utf-8").splitlines()):
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        m = re.match(r'^(?:export\s+)?XCODE_APP="([^"]+)"', s)
        if m:
            return m.group(1)
    raise SystemExit('!! config.sh 中未找到有效的 XCODE_APP="..." 配置行')


XCODE = Path(_read_xcode_app())
SCAN = ["Contents/Frameworks", "Contents/SharedFrameworks", "Contents/PlugIns"]
# 工具目录 = 脚本所在目录（动态，任意位置可用）
TOOL = Path(__file__).resolve().parent
TABLE = json.loads((TOOL / "translations/plugindata-IDEKit.json").read_text(encoding="utf-8"))


def titles_of(p: Path):
    data = plistlib.loads(p.read_bytes())
    out = []

    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k in ("title", "overrideTitle") and isinstance(v, str) and v.strip():
                    out.append(v)
                else:
                    walk(v)
        elif isinstance(o, list):
            for i in o:
                walk(i)

    walk(data)
    return set(out)


def has_cjk(s: str) -> bool:
    return any("\u4e00" <= ch <= "\u9fff" for ch in s)


def is_internal_id(t: str) -> bool:
    # 点分内部标识（命令/菜单系统 ID，非显示文本）
    return ("CmdDefinition." in t or "MenuDefinition." in t or "GeniusCategory." in t
            or t.startswith(("Xcode.", "GPUDebugger.", "com.apple.", "RCPIDESupportUI.",
                              "IDESceneKitEditor.Menu", "DVT", "IDEKit.")))


all_titles = {}
nfiles = 0
for d in SCAN:
    for f in sorted((XCODE / d).rglob("*.xcplugindata")):
        nfiles += 1
        for t in titles_of(f):
            all_titles.setdefault(t, []).append(f.stem.replace(".xcplugindata", ""))

EXEMPT = {"SourceKit", "Radar (AppleInternal)", "MissingEditorMenu", "viewDidLoad"}
known = {t for t in TABLE if not t.startswith("Xcode.")}
todo = sorted(
    t for t in all_titles
    if t not in known and not has_cjk(t) and not is_internal_id(t) and t not in EXEMPT
)
print(f"文件数: {nfiles}, 唯一 title: {len(all_titles)}, 已翻可复用: {len(all_titles) - len(todo)}, 待翻新增: {len(todo)}")
print("\n=== 待翻清单（模块 -> 次数最多的优先）===")
for t in sorted(todo, key=lambda y: -len(all_titles[y])):
    mods = ",".join(sorted(set(all_titles[t]))[:3])
    print(f"{t}\t[{mods}]")
