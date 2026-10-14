# Xcode 中文语言包（Xcode-Chinese-Language-Pack）

让 Xcode 27 的菜单栏、右键菜单、各级命令变成简体中文。

- 适用：**Xcode 27+**（在 27.0 27A266a 开发测试）· macOS 26+
- 机制：只改命令标题数据（xcplugindata），**不动任何二进制**，安装前自动备份，可一键完整回滚

## 注意：运行前提：设置-隐私管理-App管理-终端（开）
## 安装（3 步）

1. 下载或 clone 本仓库（zip 解压即可）
2. **双击 `install.command`**
   - 每次运行自动检测：Xcode 路径变化 / Xcode 版本更新 / 翻译表更新，任一变化即自动重新生成安装计划（首次使用无需任何手动步骤）
   - 拷贝时 macOS 会弹「"终端"想要修改"Xcode"」→ 点**「允许」**（可能弹多次；之后不再弹）
   - Xcode 更新后重新双击即可：会自动检测到新版本、重置备份并重新安装
3. 完全退出 Xcode（`Cmd+Q`）→ 重新打开

## Xcode 不在默认位置？

编辑本目录 `config.sh`：

```bash
XCODE_APP="/Applications/Xcode.app"   # 改成你的实际路径
```

改完重新双击 `install.command` 即可。

## 回滚 / 卸载

双击 `remove.command` → 重启 Xcode，恢复官方英文原版。

## Xcode 更新之后

App Store 更新会整体替换 Xcode.app，汉化随之丢失。重新双击 `install.command` 即可——安装器会自动检测到版本变化，重置备份并重新安装（需要 python3，装过 Xcode/命令行工具就有）。

## 工作原理

Xcode 27 的菜单/命令标题存在各 framework 的 `xcplugindata`（二进制 plist）的 `title`/`overrideTitle` 字段——传统的 `.strings` 本地化文件在 Xcode 27 中不被读取（这就是老一代 Xcode 汉化包全部失效的原因）。

本包做两件事：

1. **主包中文声明**：给 `Xcode.app/Contents/Resources/` 加一个 `zh_CN.lproj`，让 app 界面语言切换为简体中文（系统标准件如「服务」菜单跟随变中文）
2. **标题直写**：把 57 个 xcplugindata、1706 处菜单/命令标题替换为中文（源文件永远从自动备份的原始版本生成，保证幂等与可重装）

## 覆盖范围与限制

**已覆盖**：菜单栏全部顶层菜单、各级下拉命令、右键菜单、调试器、源代码管理、构建阶段/规则/能力、编辑器重构、Interface Builder 检查器、Core Data 模型编辑器、字符串目录、测试计划、Playground、属性列表/十六进制编辑器、StoreKit、书签等

**未覆盖**（技术限制）：部分 nib 界面文件中的静态布局文本、SwiftUI 硬编码文本（如部分设置页）

平台名（iOS/macOS）、格式名（PDF/HTML）、专有名词（Playground/Markdown）有意保留英文。

## 参与贡献

翻译库在 `translations/plugindata-*.json`（约 1900 条）。流程：

```
编辑翻译表 → python3 apply_plugindata.py → python3 audit.py（质检）→ install.command
```

守则：只翻 `title`/`overrideTitle`；`name`/`id`/点分标识符（`Xcode.*`、`CmdDefinition.*` 等）**永不翻**。

## 免责声明

本工具修改 Xcode.app 内的资源文件（安装前自动备份原始文件）。因苹果代码签名校验机制，个别环境下可能需要重新授权或重装 Xcode。使用本工具产生的任何风险由使用者自行承担。
