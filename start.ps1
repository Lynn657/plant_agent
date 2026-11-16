$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "[PlantAgent] 正在创建 Python 虚拟环境..."
    python -m venv .venv
}
Write-Host "[PlantAgent] 启动工作台..."
& ".venv\Scripts\python.exe" run.py
