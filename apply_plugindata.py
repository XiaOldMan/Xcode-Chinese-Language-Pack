#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全量生成翻译版 xcplugindata：遍历主包 155 个文件，title/overrideTitle 查表替换。
翻译表 = plugindata-IDEKit.json + plugindata-extra1.json + plugindata-extra2.json。"""
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
if not XCODE.exists():
    import sys
    print(f"!! 未找到 Xcode: {XCODE}\n   请编辑 config.sh 中的 XCODE_APP 为实际安装路径")
    sys.exit(1)
SCAN = ["Contents/Frameworks", "Contents/SharedFrameworks", "Contents/PlugIns"]

TABLE = {}
import glob as _glob
for _p in sorted((TOOL / "translations").glob("*.json")):
    TABLE.update(json.loads(_p.read_text(encoding="utf-8")))

INTERNAL_HINTS = ("CmdDefinition.", "MenuDefinition.", "GeniusCategory.")
INTERNAL_PREFIX = ("Xcode.", "GPUDebugger.", "com.apple.", "RCPIDESupportUI.",
                  "IDESceneKitEditor.Menu", "DVT", "IDEKit.")

# 宽松匹配表：尾部省略号/句点归一化（Add Files ↔ Add Files…），供 name 与 strings 双路使用
NTABLE = {}
for _k, _v in TABLE.items():
    NTABLE.setdefault(re.sub(r"[… .!]+$", "", _k), _v)


def replace_titles(obj, stat):
    if isinstance(obj, dict):
        has_name_title = "name" in obj and isinstance(obj.get("title"), str)
        for k, v in obj.items():
            if k in ("title", "overrideTitle") and isinstance(v, str) and v.strip():
                if any(h in v for h in INTERNAL_HINTS) or v.startswith(INTERNAL_PREFIX):
                    continue  # 点分内部标识不翻
                if v in TABLE:
                    obj[k] = TABLE[v]
                    stat[0] += 1
                elif v.strip() in TABLE:
                    lead = v[: len(v) - len(v.lstrip())]
                    obj[k] = lead + TABLE[v.strip()]
                    stat[0] += 1
                else:
                    stat[1] += 1
            else:
                replace_titles(v, stat)
        # 关键修复：部分动态命令菜单显示 name 而非 title（如 Find in Workspace），
        # name 查翻译表命中才翻（表即白名单，真标识符不在表中自然跳过）；
        # 宽松匹配：尾部省略号/句点差异 + 直/智能引号归一化（Add Files ↔ Add Files…）
        if has_name_title:
            nv = obj["name"]
            if isinstance(nv, str):
                t = TABLE.get(nv) or NTABLE.get(re.sub(r"[… .!]+$", "", nv))
                if t is None:
                    _q = nv.replace("\u201c", '"').replace("\u201d", '"').replace("\u2019", "'")
                    if _q != nv:
                        t = TABLE.get(_q)
                if t and not any(h in nv for h in INTERNAL_HINTS) and not nv.startswith(INTERNAL_PREFIX):
                    obj["name"] = t
                    stat[0] += 1
    elif isinstance(obj, list):
        for i in obj:
            replace_titles(i, stat)


plan_lines = []
total_hit = total_miss = nfiles = 0

# 源优先读原始备份（包内可能已被改成中文，重跑会导致计划不完整）
backup_map = {}
bp = TOOL / "backup-pd" / "plan.tsv"
if bp.exists():
    for line in bp.read_text(encoding="utf-8").splitlines():
        if "\t" in line:
            b, d = line.split("\t", 1)
            # 兼容相对/绝对两种备份路径格式（开源后用户可能携带旧格式）
            b = b.strip()
            if not b.startswith("/"):
                b = str(TOOL / b)
            backup_map[d.strip()] = b

for d in SCAN:
    for f in sorted((XCODE / d).rglob("*.xcplugindata")):
        nfiles += 1
        src_file = Path(backup_map.get(str(f), str(f)))
        if not src_file.exists():
            src_file = f
        data = plistlib.loads(src_file.read_bytes())
        stat = [0, 0]
        replace_titles(data, stat)
        if stat[0] == 0:
            continue
        rel = f.relative_to(XCODE)
        out = TOOL / "stage" / "PD_ALL" / str(rel).replace("/", "_")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(plistlib.dumps(data, fmt=plistlib.FMT_BINARY))
        plan_lines.append(f"{out.relative_to(TOOL)}\t{f}")
        total_hit += stat[0]
        total_miss += stat[1]

(TOOL / "stage" / "plan-pd.tsv").write_text("\n".join(plan_lines) + "\n", encoding="utf-8")
print(f"文件 {nfiles} 个，替换 {total_hit} 处，未命中 {total_miss} 处，计划 {len(plan_lines)} 行")

# 写入指纹标记（路径+构建版本），供 install 检测变化自动重新生成
try:
    _ver = plistlib.loads((XCODE / "Contents" / "version.plist").read_bytes()).get("ProductBuildVersion", "")
except Exception:
    _ver = ""
(TOOL / "stage").mkdir(exist_ok=True)
(TOOL / "stage" / ".xcode-marker").write_text(f"{XCODE}\n{_ver}\n", encoding="utf-8")

# ══ strings 中文层：打开项目后动态注入的菜单项走运行时 NSLocalizedString 查 .strings 表 ══
# 实测 Xcode 进程不读子框架 zh_CN.lproj（preferred 锁 en）→ 唯一有效方式=en 表直写
# 生成「翻译版 en.lproj」到 stage（翻译源=同一套翻译表，宽松匹配去尾部省略号）
import re as _re

FMT_RE = _re.compile(r"%(?:\d+\$)?[@dDuUfFsSxXoOeEgGcCaA]|%%")


def _fmt_tokens(s: str) -> dict:
    """占位符规范化：非位置参数按出现顺序赋序号，与 %N$@ 等价比较。
    例：'%@...%@' 与 '%1$@...%2$@' 规范化后相同。"""
    out = {}
    auto = 0
    for m in _re.finditer(r"%(?:(\d+)\$)?[@dDuUfFsSxXoOeEgGcCaA]", s):
        if m.group(1):
            out[int(m.group(1))] = m.group(0).split("$")[-1]
        else:
            auto += 1
            out[auto] = m.group(0)[1:]
    return out

# strings 源备份映射（包内可能已被直写为中文）
en_backup_map = {}
ebp = TOOL / "backup-en-strings" / "plan.tsv"
if ebp.exists():
    for line in ebp.read_text(encoding="utf-8").splitlines():
        if "\t" in line:
            b, dst = line.split("\t", 1)
            b = b.strip()
            if not b.startswith("/"):
                b = str(TOOL / b)
            en_backup_map[dst.strip()] = b

plan_str = []
s_hit = s_miss = 0
s_miss_set = {}

# 运行时键注入：部分菜单标题是代码里 NSLocalizedString 的 key（编译在二进制中），
# strings 表无此键时直接显示 key 原文（英文）——往 IDEKit en 表新增这些键即可让运行时查到中文
EXTRA_RUNTIME_KEYS = {
    "Close Window": "关闭窗口",
    "Close \"%@\"": "关闭“%@”",
    "Close “%@”": "关闭“%@”",
    "Open in New Tab": "在新标签页中打开",
    "Open in New Window": "在新窗口中打开",
    "Workspace Settings": "工作区设置",
    "Workspace Settings...": "工作区设置…",
    "Add Files": "添加文件",
    "Export": "导出",
    "Export...": "导出…",
    "New File from Clipboard": "从剪贴板新建文件",
    "Bookmark \"%@\"": "给“%@”添加书签",
    "Bookmark “%@”": "给“%@”添加书签",
    "Bookmark %@": "给%@添加书签",
    "Find in Selected File...": "在所选文件中查找…",
    "Find in Selected File…": "在所选文件中查找…",
    "Find in Selected %@...": "在所选%@中查找…",
    "Find in Selected Folder...": "在所选文件夹中查找…",
    "Add Files to \"%@\"...": "将文件添加到“%@”…",
    "Add Files to \"%@\"": "将文件添加到“%@”…",
    "Add Files to “%@”…": "将文件添加到“%@”…",
    "Add Files to %@...": "将文件添加到“%@”…",
    "Project Navigator Help": "工程导航器帮助",
}

for d in SCAN:
    for f in sorted((XCODE / d).rglob("*.strings")):
        s = str(f)
        if "en.lproj" not in s or f.name == "InfoPlist.strings":
            continue
        # 源优先读原始备份（包内可能已被直写为中文，重读会导致命中率暴跌）
        _src = Path(en_backup_map.get(s, s))
        if not _src.exists():
            _src = f
        try:
            orig = plistlib.loads(_src.read_bytes())
        except Exception:
            continue
        if not isinstance(orig, dict) or not orig:
            continue
        new = {}
        hit = 0
        for k, v in orig.items():
            if not isinstance(v, str):
                new[k] = v
                continue
            t = TABLE.get(v) or NTABLE.get(_re.sub(r"[… .!]+$", "", v))
            # 占位符强校验（序号等价：%@ 与 %N$@ 等同）
            if t and _fmt_tokens(v) == _fmt_tokens(t):
                new[k] = t
                hit += 1
            else:
                new[k] = v
                if v.strip() and any(c.isalpha() for c in v):
                    s_miss_set[v] = s_miss_set.get(v, 0) + 1
        s_hit += hit
        s_miss += len(orig) - hit
        # 运行时键注入（仅 IDEKit 主 UI 表）
        if f.name == "Localizable.strings" and f.parent.parent.name == "Resources" and "IDEKit.framework" in s:
            added = 0
            for ek, ev in EXTRA_RUNTIME_KEYS.items():
                if ek not in new:
                    new[ek] = ev
                    added += 1
            if added:
                hit += added
                s_hit += added
        if hit == 0:
            continue
        endir = f.parent  # en.lproj 目录本身（直写替换原表）
        rel_dir = endir.relative_to(XCODE)
        staging = TOOL / "stage" / "STRINGS_EN" / str(rel_dir).replace("/", "_")
        (staging / "en.lproj").mkdir(parents=True, exist_ok=True)
        (staging / "en.lproj" / f.name).write_bytes(
            plistlib.dumps(new, fmt=plistlib.FMT_BINARY, sort_keys=True)
        )
        plan_str.append(f"{staging.relative_to(TOOL) / 'en.lproj' / f.name}\t{f}")

# 主包运行时键表：主菜单动态项（Close Window/Add Files/Open in New Tab 等）的
# NSLocalizedString 查的是 mainBundle（Xcode.app 本体）的表——原包无 Localizable.strings，新建注入
# 主包运行时键表：主菜单动态项的 NSLocalizedString 查 mainBundle 的表。
# 主包 app 语言已为简中（门票）→ 查表优先 zh_CN.lproj；双写 en+zh_CN 双保险。
_main_content = dict(EXTRA_RUNTIME_KEYS)
_main_content.update({
    "Add Files to \"%@\"": "将文件添加到“%@”…",
    "Add Files to “%@”…": "将文件添加到“%@”…",
    "Close Tab": "关闭标签页",
    "Close \"%@\"...": "关闭“%@”…",
    "Workspace": "工作区",
    "New File from Clipboard": "从剪贴板新建文件",
    "Bookmark \"%@\"": "给“%@”添加书签",
    "Bookmark “%@”": "给“%@”添加书签",
    "Find in Selected File…": "在所选文件中查找…",
    "Find in Selected File...": "在所选文件中查找…",
    "Project Navigator Help": "工程导航器帮助",
    "Open in New Tab": "在新标签页中打开",
    "Open in New Window": "在新窗口中打开",
    "Close Window": "关闭窗口",
    "Workspace Settings...": "工作区设置…",
})
for _lang in ("en.lproj", "zh_CN.lproj"):
    _main_dir = TOOL / "stage" / "STRINGS_EN" / "APP_MAIN" / _lang
    _main_dir.mkdir(parents=True, exist_ok=True)
    (_main_dir / "Localizable.strings").write_bytes(
        plistlib.dumps(_main_content, fmt=plistlib.FMT_BINARY, sort_keys=True)
    )
    plan_str.append(f"{_main_dir.relative_to(TOOL) / 'Localizable.strings'}\t{XCODE / 'Contents' / 'Resources' / _lang / 'Localizable.strings'}")

(TOOL / "stage" / "plan-en-strings.tsv").write_text("\n".join(plan_str) + "\n", encoding="utf-8")
with open(TOOL / "stage" / "strings-miss.txt", "w", encoding="utf-8") as f:
    for v, n in sorted(s_miss_set.items(), key=lambda x: -x[1]):
        f.write(f"{v}\n")
print(f"strings en直写: 命中 {s_hit} 条，未命中保留英文 {s_miss} 条，文件 {len(plan_str)} 个，未翻清单 {len(s_miss_set)} 条")
