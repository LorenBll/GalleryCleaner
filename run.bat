@echo off
echo Starting GalleryCleaner Application...
echo.

:: Check if virtual environment exists
if not exist ".venv" (
    echo ERROR: Virtual environment not found!
    echo Please run setup.bat first to create the virtual environment.
    pause
    exit /b 1
)

:: Activate virtual environment
echo Activating virtual environment...
call .venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo ERROR: Failed to activate virtual environment
    pause
    exit /b 1
)

:: Check if main.py exists
if not exist "src\main.py" (
    echo ERROR: main.py not found in src directory
    pause
    exit /b 1
)

:: Run the application
python src\main.py

:: Check if the application ran successfully
if %errorlevel% neq 0 (
    echo.
    echo Application exited with an error (code %errorlevel%)
    pause
    exit /b %errorlevel%
)

pause
