@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo [PlantAgent] 正在创建 Python 虚拟环境...
  python -m venv .venv
)
echo [PlantAgent] 启动工作台...
".venv\Scripts\python.exe" run.py
if errorlevel 1 pause
endlocal
