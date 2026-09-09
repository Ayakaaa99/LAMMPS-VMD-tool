@echo off
setlocal
cd /d "%~dp0"

:: 检查 Python 是否可用
set "PYTHON_CMD=python"
where %PYTHON_CMD% >nul 2>&1
if errorlevel 1 (
    set "PYTHON_CMD=py"
    where %PYTHON_CMD% >nul 2>&1
    if errorlevel 1 (
        echo ==============================================================================
        echo   [ERROR] 未检测到 Python 运行环境！
        echo   请确保已安装 Python 并将其勾选添加到系统环境变量 PATH。
        echo ==============================================================================
        pause
        exit /b 1
    )
)

echo ==============================================================================
echo   正在启动 LAMMPS Data to VMD Visualizer 图形界面...
echo ==============================================================================

if not "%~1"=="" (
    %PYTHON_CMD% run_gui.py "%~1" --launch
) else (
    %PYTHON_CMD% run_gui.py
)

if errorlevel 1 (
    echo.
    echo ==============================================================================
    echo   [提示] 程序启动失败或异常退出，请查看上方详细提示。
    echo ==============================================================================
    pause
)
