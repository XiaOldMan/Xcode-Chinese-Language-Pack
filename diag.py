#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""诊断：为什么某些已翻词条仍在 miss 清单——逐条输出未命中原因。"""
import json
import plistlib
import re
from pathlib import Path

TOOL = Path(__file__).resolve().parent
_xcode = None
for _line in reversed((TOOL / "config.sh").read_text(encoding="utf-8").splitlines()):
    _s = _line.strip()
    if _s and not _s.startswith("#") and _s.startswith("XCODE_APP="):
        _xcode = _s.split('="', 1)[1].rstrip('"')
        break
XCODE = Path(_xcode)
TABLE = {}
for _p in sorted((TOOL / "translations").glob("*.json")):
    TABLE.update(json.loads(_p.read_text(encoding="utf-8")))
NTABLE = {}
for k, v in TABLE.items():
    NTABLE.setdefault(re.sub(r"[… .!]+$", "", k), v)
FMT = re.compile(r"%(?:\d+\$)?[@dDuUfFsSxXoOeEgGcCaA]|%%")

# 从备份原版读真实 value（含真实的占位符形态），抽样诊断
bp = TOOL / "backup-en-strings" / "plan.tsv"
backup_map = {}
for line in bp.read_text(encoding="utf-8").splitlines():
    if "\t" in line:
        b, d = line.split("\t", 1)
        b = b.strip()
        if not b.startswith("/"):
            b = str(TOOL / b)
        backup_map[d.strip()] = b

samples = ["Are you sure you want to clean the build folder for ", "Add Other", "Checkout or Clone", "Arguments Passed On Launch", "Contains", "Hide Find Options"]
count = {"表无词条": 0, "占位符不符": 0, "命中": 0}
checked = 0
for d, b in backup_map.items():
    p = Path(b)
    if not p.exists():
        continue
    orig = plistlib.loads(p.read_bytes())
    for k, v in orig.items():
        if not isinstance(v, str) or not v.strip() or not any(c.isalpha() for c in v):
            continue
        t = TABLE.get(v) or NTABLE.get(re.sub(r"[… .!]+$", "", v))
        if t:
            if sorted(FMT.findall(v)) == sorted(FMT.findall(t)):
                count["命中"] += 1
            else:
                count["占位符不符"] += 1
                if count["占位符不符"] <= 8:
                    print(f"[占位符不符] 原文 {v[:60]!r}\n    原文占位 {sorted(FMT.findall(v))}\n    译文占位 {sorted(FMT.findall(t))} -> {t[:40]!r}")
        else:
            count["表无词条"] += 1
        checked += 1

print(f"\n检查 {checked} 条：{count}")
