@echo off
REM Creates a virtual environment in the project root

set SCRIPT_DIR=%~dp0
for %%I in ("%SCRIPT_DIR%..") do set PROJECT_ROOT=%%~fI
set VENV_PATH=%PROJECT_ROOT%\venv

REM Create venv if it doesn't exist
if not exist "%VENV_PATH%\Scripts\activate.bat" (
    echo Creating new virtual environment in project root...
    python -m venv "%VENV_PATH%"
) else (
    echo Existing virtual environment found.
)

echo Activating virtual environment...
call "%VENV_PATH%\Scripts\activate.bat"

echo Upgrading pip...
python -m pip install --upgrade pip

echo Installing Atlas in editable dev mode...
python -m pip install -e "%PROJECT_ROOT%"[dev]

echo Dev environment ready!
echo Your venv is now active in this shell.