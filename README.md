# LAMMPS Data VMD Viewer

一个用于在 VMD 中加载和查看 LAMMPS Data 文件的小工具。Data文件后缀包括但不限于.data，只要编码相同的格式都可用。本工具大部分使用vibe coding完成，目前主要使用的模型为Gemini-3.8-flash。

由于 LAMMPS data 文件中通常仅包含数值形式的原子类型（如 `type 1`, `type 2`），在 VMD 中通过 TopoTools 打开时容易出现所有原子均为未知元素、颜色单一或材质发灰的情况。本工具通过读取 data 文件中的 `Masses` 区域推断元素符号并赋予范德华半径与颜色，生成对应的 VMD 启动脚本或直接拉起 VMD 窗口。

---

## 主要功能

- **元素推断**：根据 `Masses` 中的原子质量或行末注释匹配化学元素（如 12.011 -> C，15.999 -> O），并设置对应的范德华半径与颜色。
- **晶胞换算**：支持正交（Orthogonal）与三斜（Triclinic 倾斜因子 $xy, xz, yz$）模拟盒子，换算为 VMD 所需的晶胞参数（$a, b, c, \alpha, \beta, \gamma$）并绘制边界。
- **样式识别**：自动检测常见 LAMMPS `atom_style`（`full`, `atomic`, `molecular`, `charge` 等）。
- **多途径使用**：支持图形界面（GUI）、终端命令行（CLI）、文件拖放，以及 VMD 内部控制台脚本。

---

## 运行环境
- Windows x86系统
- Python 3.8 及以上（仅依赖标准库）
- VMD（已测试兼容 VMD 1.9.x 及 VMD 2.0）

---

## 使用方法

### 1. 图形界面（GUI）

直接运行批处理文件或 Python 脚本：
```bash
# Windows 双击运行或在命令行执行：
run_gui.bat

# 或直接使用 Python 启动：
python run_gui.py
```

- **加载文件**：点击“浏览”选择文件，或直接把 `.data` 文件拖入窗口。
- **修改参数**：在表格中双击原子类型可手动修改元素或半径；在“视觉预设与晶胞”页面中可切换显示样式（CPK、VDW、Licorice）与背景颜色。
- **启动展示**：点击“一键在 VMD 中展示”，或点击“导出 .vmd 脚本”保存生成的 Tcl 文件。

### 2. 文件拖放运行

用户可以直接将任意格式Data文件拖拽到 `拖动Data文件到此.bat` 图标上，脚本会直接生成临时文件并拉起 VMD 展示。

### 3. 命令行（CLI）

适合习惯终端或批量处理的用户(例)：

```bash
# 生成 VMD 加载脚本（默认输出为 <原文件名>_view.vmd）
python -m lammps_vmd_tool.cli.main examples/water_full.data

# 生成脚本后直接拉起 VMD
python -m lammps_vmd_tool.cli.main examples/water_full.data -l

# 手动指定元素映射（覆盖自动推断）
python -m lammps_vmd_tool.cli.main data.system -m "1:C,2:H,3:O" -l

# 手动指定 VMD 执行文件路径
python -m lammps_vmd_tool.cli.main data.system -l --vmd-path "C:\Program Files\VMD\vmd.exe"
```

#### 命令行参数说明

| 参数 | 说明 |
| :--- | :--- |
| `data_file` | LAMMPS data 文件路径 |
| `-s, --style` | 强制指定 atom_style（如 full, atomic, molecular, charge 等） |
| `-p, --preset` | 显示预设（publication, ball_and_stick, vdw_spacefill, licorice） |
| `-m, --mapping` | 自定义元素映射，格式为 `"1:C,2:H,3:O"` |
| `-o, --output` | 指定导出的 `.vmd` 脚本文件名 |
| `-l, --launch` | 生成后自动拉起 VMD 运行 |
| `--vmd-path` | 指定 `vmd.exe` 的本地完整路径 |
| `--bg` | 指定背景色（white, black） |
| `--no-box` | 不绘制模拟盒子边界线 |


## 目录结构

```
├── lammps_vmd_tool/            # Python 包
│   ├── core/                   # 数据解析、晶胞几何计算、元素匹配与脚本生成
│   ├── gui/                    # Tkinter 图形界面与拖放支持
│   └── cli/                    # 命令行入口
├── vmd_plugin/
│   └── lammps_loader.tcl       # VMD 原生 Tcl 加载脚本
├── examples/                   # 测试示例文件（包含水、石墨烯、石英）
├── tests/                      # 单元测试
├── run_gui.bat                 # GUI 启动批处理
├── drop_to_vmd.bat             # 拖放快速启动批处理
├── run_gui.py                  # Python 启动入口
├── .gitignore
└── README.md
```

---

## 注意事项

1. **VMD 路径**：初次在 GUI 中点击展示时，若系统环境变量 `PATH` 中未包含 VMD，可在界面左下角点击“配置 VMD 路径”选择 `vmd.exe`，该路径会自动记录到用户主目录配置文件中，无需重复设置。
2. **三斜晶胞**：若文件中包含 `xy xz yz` 倾斜因子，工具会自动将其转为 VMD 的六个晶胞参数（边长及夹角），并通过 `molinfo` 与 `pbctools` 进行设置。
