@echo off
setlocal enabledelayedexpansion
title OmniTool Setup and Launch

echo =======================================================
echo          OmniTool ? 100%% Local Media Suite
echo =======================================================
echo.

set "PY_CMD="

:: 1. Check if a local .venv already exists
if exist ".venv\Scripts\python.exe" (
    echo [1/3] Using local virtual environment (.venv)...
    set "PY_CMD=.venv\Scripts\python.exe"
    goto :run_app
)

:: 2. Search for system Python
where python >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set "PY_CMD=python"
    goto :setup_venv
)

where py >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set "PY_CMD=py"
    goto :setup_venv
)

if exist "%LOCALAPPDATA%\Programs\Python\Python310\python.exe" (
    set "PY_CMD=%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
    goto :setup_venv
)

for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*") do (
    if exist "%%D\python.exe" (
        set "PY_CMD=%%D\python.exe"
        goto :setup_venv
    )
)

:: If Python is not found, offer to install via winget
echo [!] Python 3 was not found on this computer.
echo Attempting to install Python via Windows Package Manager (winget)...
winget install --id Python.Python.3.10 -e --source winget --accept-source-agreements --accept-package-agreements
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Failed to auto-install Python. Please install Python 3.10+ from python.org and check 'Add Python to PATH'.
    pause
    exit /b 1
)
set "PY_CMD=python"

:setup_venv
echo [2/3] Setting up local isolated environment (.venv)...
"%PY_CMD%" -m venv .venv
if %ERRORLEVEL% NEQ 0 (
    echo [WARNING] Could not create .venv, running with global python...
    goto :install_deps_global
)

echo Installing required packages (CustomTkinter, PyMuPDF, Pillow, FFmpeg)...
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt
set "PY_CMD=.venv\Scripts\python.exe"
goto :run_app

:install_deps_global
echo Installing dependencies into system Python...
"%PY_CMD%" -m pip install -r requirements.txt

:run_app
echo [3/3] Launching OmniTool Suite...
echo.
"%PY_CMD%" main.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [!] OmniTool stopped with an error (Code: %ERRORLEVEL%).
    pause
)
