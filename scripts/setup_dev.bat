@echo off
REM Creates a virtual environment in the project root

set SCRIPT_DIR=%~dp0
for %%I in ("%SCRIPT_DIR%..") do set PROJECT_ROOT=%%~fI
set VENV_PATH=%PROJECT_ROOT%\venv

REM If venv exists, activate it. Otherwise create it.
if exist "%VENV_PATH%\Scripts\activate.bat" (
    echo Existing virtual environment found.
) else (
    echo Creating new virtual environment in project root...
    python -m venv "%VENV_PATH%"
)

echo Activating virtual environment...
call "%VENV_PATH%\Scripts\activate.bat"

echo Upgrading pip...
python -m pip install --upgrade pip

echo Installing Atlas in editable dev mode...
python -m pip install -e "%PROJECT_ROOT%"[dev]

echo Installing dev tools (Black, Ruff, Flake8, PyInstaller, pytest, PyQt6)...
pip install black ruff flake8 pyinstaller pytest PyQt6

echo Dev environment ready!
echo Your venv is now active in this shell.