@echo off
setlocal enabledelayedexpansion

REM Start GalleryCleaner.

set VERBOSE=0
if "%1"=="--verbose" (
  set VERBOSE=1
)

pushd "%~dp0\.."

REM Check Python 3.10+.
where python >nul 2>&1
if errorlevel 1 (
  if %VERBOSE% equ 1 echo ERROR: Python not installed or not on PATH.
  popd
  exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i

for /f "tokens=1,2 delims=." %%a in ("%PYTHON_VERSION%") do (
  set MAJOR=%%a
  set MINOR=%%b
)

if not defined MAJOR (
  if %VERBOSE% equ 1 echo ERROR: Could not determine Python version.
  popd
  exit /b 1
)

if "%MAJOR%" lss "3" (
  if %VERBOSE% equ 1 echo ERROR: Python 3.10+ required; found %PYTHON_VERSION%
  popd
  exit /b 1
)

if "%MAJOR%" equ "3" if "%MINOR%" lss "10" (
  if %VERBOSE% equ 1 echo ERROR: Python 3.10+ required; found %PYTHON_VERSION%
  popd
  exit /b 1
)

if %VERBOSE% equ 1 echo Python %PYTHON_VERSION% detected.

REM Create or reuse virtual environment.
if not exist ".venv" (
  if %VERBOSE% equ 1 echo Creating virtual environment...
  python -m venv .venv
  if errorlevel 1 (
    if %VERBOSE% equ 1 echo ERROR: Failed to create virtual environment.
    popd
    exit /b 1
  )
  if %VERBOSE% equ 1 echo Virtual environment created.
)

REM Activate virtual environment.
if not exist ".venv\Scripts\activate.bat" (
  if %VERBOSE% equ 1 echo ERROR: Virtual environment activation script not found at .venv\Scripts\activate.bat
  popd
  exit /b 1
)

call ".venv\Scripts\activate.bat"
if errorlevel 1 (
  if %VERBOSE% equ 1 echo ERROR: Failed to activate virtual environment.
  popd
  exit /b 1
)
if %VERBOSE% equ 1 echo Virtual environment activated.

set PYTHON_EXE=%CD%\.venv\Scripts\python.exe
if not exist "%PYTHON_EXE%" (
  if %VERBOSE% equ 1 echo ERROR: Python executable not found at %PYTHON_EXE%
  popd
  exit /b 1
)

REM Install or upgrade dependencies.
if %VERBOSE% equ 1 echo Installing dependencies...
python -m pip install --quiet --upgrade pip >nul 2>&1
python -m pip install --quiet -r requirements.txt >nul 2>&1
if %VERBOSE% equ 1 echo Dependencies installed.

REM Start GalleryCleaner.
if %VERBOSE% equ 1 (
  echo.
  echo GalleryCleaner starting...
  echo.
  "%PYTHON_EXE%" src/main.py
) else (
  start "" /B "%PYTHON_EXE%" src/main.py >nul 2>&1
  echo GalleryCleaner started in background. Run 'run.bat --verbose' to see output.
)

popd
endlocal
