# LAMMPS → VMD

LAMMPS data 文件与文本轨迹文件（dump）的 VMD 可视化启动器。

程序读取文件中的原子类型、质量、元素、半径和晶胞信息，在窗口中完成颜色与显示设置，然后生成 Tcl 脚本交给 VMD 执行。导入文件后不会自动启动 VMD，由使用者确认参数后手动打开。

当前版本：0.0.2

## 功能

### 输入

- LAMMPS data 文件：支持正交与三斜晶胞，读取 `Masses`、`Atoms` 及各类拓扑计数。
- LAMMPS 文本 dump：支持 `atom` / `custom` 风格与多帧轨迹，通过 VMD 自带 `lammpstrj` 插件读取。
- 不按后缀过滤文件，按内容判断是 data 还是 dump；`.data`、`.lmp`、`.sys`、`.dump`、`.lammpstrj` 或其他后缀均可。
- 严格按 UTF-8 解码。检测到非 UTF-8 内容时弹出“编码错误”，不使用替换字符静默继续。

### 解析与映射

- 根据 `Masses` 的质量与行末注释推断元素，并据此设置 VMD 元素名与范德华半径。
- dump 文件若包含 `element` 列则使用该列；否则使用内置调色板作为类型默认色。
- 原子颜色通过色块显示和取色器选择，脚本中以精确 RGB 写入，不依赖 VMD 颜色名。
- 原子类型列表提供类型、质量、半径和文件注释；半径可直接编辑。
- 界面不展示 atom style 或元素匹配列，atom style 由列数自动推断。

### 显示

- 表示方式：CPK、VDW、Licorice、DynamicBonds、Lines。
- 可调球体缩放与键半径。
- 四组预设：期刊、深色、填充、骨架。
- 背景颜色、正交/透视投影、晶胞边框开关与边框颜色。
- 无键体系在 CPK / Licorice / Lines 表示下会叠加 DynamicBonds 距离键。
- 可导出生成的 `.vmd` 脚本。

### VMD 交互

- 支持拖入窗口、拖到 exe 图标、点击选择文件；导入后只解析和展示参数。
- 点击“在 VMD 中显示”后才启动 VMD。
- 自动检测 VMD 路径，也可手动指定 `vmd.exe`；路径保存在用户目录。
- data 文件通过 TopoTools 读取，脚本会依次尝试 `full / molecular / bond / angle / charge / atomic / dipole`，无需手动选择 atom style。
- 脚本通过 VMD 的 Tcl / Tk Console 机制执行，并尝试自动打开 Tk Console，便于继续手动调整。

## 运行环境

- 预编译 exe：Windows x64，无需安装 Python，需要本机已安装 VMD。
- 源码运行：仅使用标准库，语法兼容 Python 3.8+；开发与打包环境为 Python 3.12。
- VMD：开发与验证使用 VMD 2.0（Windows x64）。data 文件需要 TopoTools，晶胞边框需要 pbctools；官方 VMD 发行版通常已包含。VMD 1.9.x 通常也具备这些组件，但未逐一验证。
- 拖放功能仅在 Windows 下可用；源码在 macOS / Linux 可打开界面，但没有原生拖放。

## 使用

### 预编译 exe

1. 运行 `LAMMPS-VMD.exe`。
2. 将 LAMMPS 文件拖入窗口任意位置，或拖到 exe 图标上，或点击选择文件。
3. 在窗口中调整颜色、表示方式、背景、投影和晶胞边框。
4. 点击“在 VMD 中显示”生成脚本并启动 VMD。

首次运行若未检测到 VMD，点击右上角“VMD 路径”选择 `vmd.exe`。路径会写入用户主目录的 `.lammps_vmd_tool.json`，后续自动复用。

### 从源码运行

```bash
python run_gui.py
python run_gui.py path/to/lammps.data
```

传入文件参数时仅加载文件，不自动启动 VMD。

## 文件识别与编码

- 文件类型由内容判断：出现 LAMMPS dump 的 `ITEM:` 结构视为轨迹，否则按 data 文件解析。
- 输入允许任意后缀，但内容必须是 UTF-8 文本。
- 仅支持文本 dump。二进制 dump、压缩文件（如 `.gz`）以及 GBK / UTF-16 文本会加载失败并提示编码或格式错误。

## 生成的 VMD 脚本

- 脚本由 VMD 以 `vmd -e` 方式执行。
- data 文件：TopoTools 加载，脚本按检测结果优先尝试对应 atom style，失败后继续尝试其他样式。
- dump 文件：`mol new <path> type lammpstrj waitfor all` 读取多帧。
- 设置晶胞参数，按类型写入精确 RGB、元素名和半径。
- 多帧轨迹在帧切换时重新应用半径。
- 可选绘制 `pbc box` 晶胞边框。
- 无键体系按需添加 DynamicBonds 表示。
- 结束时尝试执行 `menu tkcon on`。

## 构建

```powershell
python -m PyInstaller --noconfirm --clean --onefile --windowed --name "LAMMPS-VMD" --icon assets/app.ico --add-data "assets/app.ico;assets" run_gui.py
```

产物为 `dist/LAMMPS-VMD.exe`。`dist/` 与 `build/` 已加入 `.gitignore`，构建产物不进入源码仓库。

## 发布

`dist/LAMMPS-VMD.exe` 是 PyInstaller 单文件产物，可直接作为 GitHub Release 附件上传，不需要提交到源码仓库。

建议：

- 附件名包含版本与平台，例如 `LAMMPS-VMD-0.0.2-win64.exe`。
- 同时提供 SHA256 校验值。
- exe 未签名，Windows SmartScreen 可能显示未知发布者提示。
- 如需可复现构建，可在 GitHub Actions 的 Windows runner 上执行上面的打包命令。

## 测试

```bash
python -m unittest discover -s tests -v
```

当前包含 18 个单元测试，覆盖 data / dump 解析、三斜晶胞换算、元素推断、UTF-8 错误与 Tcl 脚本生成。

## 目录结构

```
assets/app.ico                    应用图标
dist/                             PyInstaller 输出（不提交）
examples/                         示例 data 文件
lammps_vmd_tool/core/parser.py    data / dump 解析，UTF-8 校验
lammps_vmd_tool/core/box_math.py  晶胞参数换算
lammps_vmd_tool/core/periodic_table.py  元素数据与推断
lammps_vmd_tool/core/vmd_generator.py   VMD Tcl 脚本生成
lammps_vmd_tool/core/launcher.py  VMD 路径检测与启动
lammps_vmd_tool/gui/app.py        主窗口与交互
lammps_vmd_tool/gui/theme.py      Win11 风格主题与自绘控件
lammps_vmd_tool/gui/dnd.py        Windows 原生拖放
tests/                            单元测试
vmd_plugin/lammps_loader.tcl      原有 VMD 内部控制台插件（保持原样）
run_gui.py                        源码 / 打包入口
PROJECT_HISTORY.md                项目历史与开发记录
```

## 已知限制

- 仅支持文本格式的 LAMMPS dump；二进制与压缩轨迹不支持。
- VMD 的 `lammpstrj` 插件要求各帧原子数一致，原子数变化的轨迹会读取失败。
- 只支持 TopoTools 能处理的 atom style；`hybrid` 等复杂样式不在支持范围内。
- 单独加载 dump 时没有键拓扑，只能通过距离键显示成键关系；不会自动关联同名 data 文件。
- 预编译 exe 未签名，Windows SmartScreen 可能显示未知发布者提示。
- 界面与拖放主要面向 Windows；其他平台仅保证源码可启动。

## 项目历史

与先前版本的差异和改动记录见 [PROJECT_HISTORY.md](PROJECT_HISTORY.md)。功能说明以本文件为准。
