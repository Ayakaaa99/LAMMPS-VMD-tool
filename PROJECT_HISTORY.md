# 改动记录

- 当前版本：0.0.2
- 对比基线：仓库提交 `v0.0.1`
- 说明：这里只记录与上一版的差异、改动原因和修改约束；功能、用法、构建方式见 README。

## 0.0.1 → 0.0.2 的主要差异

| 方面 | 0.0.1 | 0.0.2 |
| --- | --- | --- |
| 输入文件 | 仅 data，按后缀过滤 | data + 文本 dump；按内容识别，不限制后缀 |
| 编码处理 | `errors="replace"`，静默替换 | 严格 UTF-8；非 UTF-8 弹窗报错 |
| 界面 | 旧版 Tkinter；显示 atom style 和元素匹配表 | Win11 风格重写；不显示 atom style / 元素列 |
| 表头 | “文件注释说明” | “注释说明” |
| 颜色 | VMD 颜色名（如 `cyan`） | 色块 + 取色器；脚本写入精确 RGB |
| VMD 启动 | 拖入即启动 / 自动启动选项 | 导入后只加载；手动点击“在 VMD 中显示” |
| 入口 | GUI + CLI + 两个 bat | 单个 exe；源码入口 `run_gui.py` |
| 拖放 | 依赖 windnd / ctypes 回退 | 纯 ctypes `WM_DROPFILES` |
| 轨迹 | 不支持 | 文本 dump，多帧，使用 VMD `lammpstrj` 插件 |
| atom style | 界面手动选择 | 由列数推断，脚本中按顺序回退 |
| 测试 | 基础解析 / 生成测试 | 增加 dump、三斜边界、UTF-8 错误、脚本 ASCII 等，共 18 个 |

## 文件变化

新增：

- `lammps_vmd_tool/gui/theme.py`：Win11 主题与自绘控件。
- `assets/app.ico`：应用图标。
- `PROJECT_HISTORY.md`：本文件。

重写：

- `core/parser.py`、`core/vmd_generator.py`
- `gui/app.py`、`gui/dnd.py`
- `core/launcher.py`（增加常见目录扫描）
- `README.md`、`tests/`

删除：

- `lammps_vmd_tool/cli/`
- `run_gui.bat`、拖放用 bat
- `_console.tcl`、`_console2.tcl`、日志、截图、空 `src/`

未改动：

- `vmd_plugin/lammps_loader.tcl`
- `core/box_math.py`、`core/periodic_table.py`

## 改动原因

- 旧界面信息层级混乱，且暴露了 atom style、元素映射等底层参数。
- 两个 bat 与 CLI 造成重复入口，改为单 exe。
- LAMMPS 文件后缀不固定，后缀过滤会排除合法文件。
- 颜色名无法直观预览，也不便于精确复现。
- 导入即启动 VMD 没有给参数调整留出时间。
- 缺少 dump 轨迹支持。

## 行为与兼容性变化

- 0.0.2 不再提供 CLI 和 bat；使用 exe，或 `python run_gui.py <file>`。
- 导入文件（拖放、选择、命令行参数）不会启动 VMD，必须点击按钮。
- 主界面不再显示 atom style 和元素匹配表。
- 输入文件不再按后缀过滤，但必须是 UTF-8 文本；dump 仅支持文本格式。
- 颜色使用自定义颜色槽写入精确 RGB，不再只写颜色名。
- 仍通过 VMD 的 Tcl / Tk Console 执行脚本，`vmd_plugin/lammps_loader.tcl` 保持原样。
- 运行时 VMD 路径配置写入用户主目录，不进入仓库。
- `dist/`、`build/`、`*.spec` 不提交；仓库文本不包含个人路径。

## 后续修改约束

1. 不恢复导入后自动启动 VMD。
2. 不在界面展示 atom style / 元素列。
3. 不增加输入文件后缀过滤；保持严格 UTF-8 校验和错误弹窗。
4. 保持精确 RGB、单 exe 和 Tk Console 执行方式。
5. 不修改 `vmd_plugin/lammps_loader.tcl`，除非有明确需求。
6. 新增文档和代码不得包含用户名、工程绝对路径或本机安装路径。

## 验证记录

- `python -m unittest discover -s tests -v`：18 个测试通过。
- 使用 VMD 2.0 文本模式验证 data / dump 脚本，可正常载入。
- exe 带文件参数启动时只加载，不启动 VMD；点击按钮后启动 VMD。
- GBK 文件触发“编码错误”弹窗。
- VMD 1.9.x 未逐一验证；当前验证环境为 VMD 2.0 Windows x64。
