【OptiCore 跨环境部署改造需求】

当前程序在别的电脑上运行时，因为 Python 路径不同、依赖缺失，导致无法启动。现需对代码和启动方式进行改造，使其在任何 Windows 电脑上都能一键运行。

---

## 一、改造目标

1. **自动查找 Python 路径**：不再硬编码 `D:\Python.exe\python.exe`，而是动态检测系统 PATH 中的 Python。
2. **自动安装依赖**：启动时检查 `streamlit`、`numpy`、`pandas`、`matplotlib` 是否已安装，如果缺失则自动用 `pip install` 安装。
3. **一键启动**：用户只需双击一个 `.bat` 文件或 `.py` 文件，程序自动完成环境准备并启动 Streamlit。

---

## 二、需要修改的文件

### 1. 删除所有硬编码路径
- 在项目中搜索 `D:\Python.exe` 或任何带盘符的 `python.exe` 绝对路径，全部删除。
- 所有 Python 调用改为使用相对命令：`python`、`python3` 或 `py`（Windows Python Launcher）。

### 2. 新增启动脚本 `run.bat`（Windows 批处理）
在项目根目录创建 `run.bat`，内容如下：

```batch
@echo off
chcp 65001 >nul
title OptiCore 光学计算软件 启动器

echo ==============================
echo   OptiCore 光学计算软件
echo   正在检测环境，请稍候...
echo ==============================
echo.

:: 检测 Python 是否可用
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python！
    echo 请安装 Python 3.12 或以上版本，并确保在安装时勾选 "Add Python to PATH"。
    echo.
    echo 下载地址：https://www.python.org/downloads/
    echo.
    pause
    exit /b
)

:: 显示 Python 版本
for /f "delims=" %%i in ('python --version 2^>^&1') do set PY_VER=%%i
echo 检测到 Python: %PY_VER%

:: 检查并安装依赖（静默安装，只显示进度）
echo.
echo 正在检查依赖库...
pip show streamlit >nul 2>&1
if errorlevel 1 (
    echo 首次运行，正在安装依赖库（约需1-2分钟）...
    pip install --quiet streamlit numpy pandas matplotlib
    if errorlevel 1 (
        echo [警告] pip 安装失败，尝试使用 python -m pip 重试...
        python -m pip install --quiet streamlit numpy pandas matplotlib
    )
    echo 依赖库安装完成！
) else (
    echo 依赖库检查通过 √
)

:: 启动 Streamlit
echo.
echo ==============================
echo   正在启动程序...
echo   浏览器将自动打开，请稍候...
echo ==============================
echo.
streamlit run app.py --server.headless true

pause