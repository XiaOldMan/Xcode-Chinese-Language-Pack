#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""加固审计 v2：基于现有三层机制做全量漏翻检查。
1) xcplugindata：title/overrideTitle/name（源=原版备份优先）中未翻的显示文本
2) strings：value 未翻清单（按模块统计）
3) 覆盖全部 155 个文件（含 hit=0 未安装的）"""
import json
import plistlib
import re
from pathlib import Path

TOOL = Path(__file__).resolve().parent
XCODE = Path(re.search(r'XCODE_APP="([^"]+)"', (TOOL / "config.sh").read_text(encoding="utf-8")).group(1))
SCAN = ["Contents/Frameworks", "Contents/SharedFrameworks", "Contents/PlugIns"]
TABLE = {}
for _p in sorted((TOOL / "translations").glob("*.json")):
    TABLE.update(json.loads(_p.read_text(encoding="utf-8")))


def has_cjk(s):
    return any("\u4e00" <= c <= "\u9fff" for c in s)


def norm(s):
    return re.sub(r"[… .!]+$", "", s)


def is_internal(t):
    return ("CmdDefinition." in t or "MenuDefinition." in t or "GeniusCategory." in t
            or t.startswith(("Xcode.", "GPUDebugger.", "com.apple.", "RCPIDESupportUI.",
                             "IDESceneKitEditor.Menu", "DVT", "IDEKit.", "IDE", "DBG"))
            or not t.strip())


def looks_display(t):
    """显示文本启发式：含空格的多词组且非点分标识/CamelCase"""
    if " " not in t or "." in t:
        return False
    words = t.split()
    return sum(1 for w in words if w[0].isupper()) >= 1 and all(w[:1].isalpha() or w[0] in "(\"'“" for w in words if w)


# 备份映射
backup_map = {}
bp = TOOL / "backup-pd" / "plan.tsv"
if bp.exists():
    for line in bp.read_text(encoding="utf-8").splitlines():
        if "\t" in line:
            b, d = line.split("\t", 1)
            b = b.strip()
            if not b.startswith("/"):
                b = str(TOOL / b)
            backup_map[d.strip()] = b

miss_title, miss_name = {}, {}
for d in SCAN:
    for f in sorted((XCODE / d).rglob("*.xcplugindata")):
        src = Path(backup_map.get(str(f), str(f)))
        if not src.exists():
            src = f
        try:
            data = plistlib.loads(src.read_bytes())
        except Exception:
            continue

        def walk(o):
            if isinstance(o, dict):
                for k, v in o.items():
                    if k in ("title", "overrideTitle") and isinstance(v, str) and v.strip():
                        if not has_cjk(v) and not is_internal(v) and v not in TABLE and norm(v) not in TABLE:
                            miss_title.setdefault(v, f.stem.replace(".xcplugindata", ""))
                    elif k == "name" and isinstance(v, str) and "title" in o:
                        if (not has_cjk(v) and not is_internal(v) and v not in TABLE
                                and norm(v) not in TABLE and looks_display(v)):
                            miss_name.setdefault(v, f.stem.replace(".xcplugindata", ""))
                    else:
                        walk(v)
            elif isinstance(o, list):
                for i in o:
                    walk(i)

        walk(data)

print(f"=== xcplugindata 未翻 title（显示文本）：{len(miss_title)} 条")
for t, m in sorted(miss_title.items()):
    print(f"  {t!r}\t[{m}]")
print(f"\n=== xcplugindata 未翻 name（疑似显示文本）：{len(miss_name)} 条")
for t, m in sorted(miss_name.items()):
    print(f"  {t!r}\t[{m}]")

# strings 未翻按模块
miss_mod = {}
sf = TOOL / "stage" / "strings-miss.txt"
if sf.exists():
    print("\n=== strings 未翻（stage/strings-miss.txt，按价值已排）===")
    print(f"共 {len(sf.read_text().splitlines())} 条，详见文件")
