@echo off
setlocal enabledelayedexpansion

REM Set up GalleryCleaner on Windows.

echo.
echo GalleryCleaner - Windows Setup
echo.

cd /d "%~dp0.."

REM Check Python 3.10+.
where python >nul 2>&1
if errorlevel 1 (
  echo ERROR: Python not installed or not on PATH.
  echo Install Python 3.10+ from https://www.python.org/downloads/
  echo Check "Add Python to PATH" during installation.
  echo.
  pause
  exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo Found Python %PYTHON_VERSION%

for /f "tokens=1,2 delims=." %%a in ("%PYTHON_VERSION%") do (
  set MAJOR=%%a
  set MINOR=%%b
)

if not defined MAJOR (
  echo ERROR: Could not determine Python version.
  echo.
  pause
  exit /b 1
)

if "%MAJOR%" lss "3" (
  echo ERROR: Python 3.10+ required; found %PYTHON_VERSION%
  echo.
  pause
  exit /b 1
)

if "%MAJOR%" equ "3" if "%MINOR%" lss "10" (
  echo ERROR: Python 3.10+ required; found %PYTHON_VERSION%
  echo.
  pause
  exit /b 1
)

echo Python version is compatible.
echo.

REM Virtual environment.
if exist ".venv" (
  echo Virtual environment exists.
  choice /C YN /M "Recreate it"
  if errorlevel 2 goto use_venv
  if errorlevel 1 (
    rmdir /s /q .venv
  )
)

:use_venv
if not exist ".venv" (
  echo Creating virtual environment...
  python -m venv .venv
  if errorlevel 1 (
    echo ERROR: Failed to create virtual environment.
    echo Install the venv module with Python, then retry.
    echo.
    pause
    exit /b 1
  )
)

REM Activate and install.
if not exist ".venv\Scripts\activate.bat" (
  echo ERROR: Virtual environment activation script not found at .venv\Scripts\activate.bat
  pause
  exit /b 1
)

call ".venv\Scripts\activate.bat"
if errorlevel 1 (
  echo ERROR: Failed to activate virtual environment.
  pause
  exit /b 1
)

echo Installing dependencies...
python -m pip install --quiet --upgrade pip >nul 2>&1
python -m pip install --quiet -r requirements.txt >nul 2>&1
if errorlevel 1 (
  echo ERROR: Failed to install dependencies.
  echo Check network and requirements.txt.
  echo.
  pause
  exit /b 1
)
echo Dependencies installed.

echo.
echo Checking configuration...
if not exist "configuration.json" (
  echo WARNING: Create configuration.json before running GalleryCleaner.
) else (
  echo Configuration file found.
)

echo.
echo ===============================================
echo   GalleryCleaner Setup Complete
echo ===============================================
echo.
echo Next: scripts\run.bat
echo.
echo For auto-start on Windows:
echo   1. Edit deployment\startup-windows.vbs (update paths)
echo   2. Win+R, type: shell:startup
echo   3. Copy startup-windows.vbs to the Startup folder
echo.
pause
endlocal
