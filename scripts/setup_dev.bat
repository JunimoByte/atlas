@echo off
REM ============================================================================
REM Atlas dev environment setup (Windows)
REM
REM  - Creates/reuses a venv in the project root
REM  - Installs dev tools (pytest, ruff, black, flake8)
REM  - Auto-detects Python version and installs PyQt6 (Python 3.9+) or PyQt5
REM  - Installs PyInstaller for building portable executables
REM ============================================================================

setlocal EnableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "PROJECT_ROOT=%%~fI"
set "VENV_PATH=%PROJECT_ROOT%\venv"

REM ---------------------------------------------------------------------------
REM 1. Create venv if it doesn't exist
REM ---------------------------------------------------------------------------
if not exist "%VENV_PATH%\Scripts\activate.bat" (
    echo Creating new virtual environment...
    python -m venv "%VENV_PATH%"
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment.
        echo Make sure Python 3.8+ is installed and on PATH.
        exit /b 1
    )
) else (
    echo Existing virtual environment found.
)

REM ---------------------------------------------------------------------------
REM 2. Activate
REM ---------------------------------------------------------------------------
echo Activating virtual environment...
call "%VENV_PATH%\Scripts\activate.bat"

REM ---------------------------------------------------------------------------
REM 3. Upgrade pip
REM ---------------------------------------------------------------------------
echo Upgrading pip...
python -m pip install --upgrade pip --quiet

REM ---------------------------------------------------------------------------
REM 4. Install dev tools (pytest, ruff, black, flake8, pytest-qt)
REM    Note: quotes wrap the full extras expression to avoid shell splitting
REM ---------------------------------------------------------------------------
echo Installing dev tools...
python -m pip install --quiet -e "%PROJECT_ROOT%[dev]"
if errorlevel 1 (
    echo ERROR: Failed to install dev dependencies.
    exit /b 1
)

REM ---------------------------------------------------------------------------
REM 5. Detect Python version and install the correct Qt binding
REM    If Windows and has Python 3.8 or older, fallback to PyQt5
REM    If Linux and has Python 3.8 or newer, use PyQt6, else fallback to PyQt5
REM ---------------------------------------------------------------------------
echo Detecting Python version for Qt binding selection...
for /f %%A in ('python -c "import sys; print(1 if sys.version_info >= (3, 9) else 0)"') do set USE_PYQT6=%%A

if "!USE_PYQT6!"=="1" (
    echo Python 3.9+ detected on Windows -- installing PyQt6...
    python -m pip install --quiet "PyQt6>=6.0"
    if errorlevel 1 (
        echo PyQt6 failed, falling back to PyQt5...
        python -m pip install --quiet "PyQt5>=5.15"
    )
) else (
    echo Python 3.8 or older detected on Windows -- installing PyQt5 for compatibility...
    python -m pip install --quiet "PyQt5>=5.15"
    if errorlevel 1 (
        echo ERROR: Failed to install PyQt5.
        exit /b 1
    )
)

REM ---------------------------------------------------------------------------
REM 6. Install PyInstaller for building portable executables
REM ---------------------------------------------------------------------------
echo Installing PyInstaller...
python -m pip install --quiet "pyinstaller>=6.0"
if errorlevel 1 (
    echo WARNING: PyInstaller installation failed.
    echo You can install it manually: pip install pyinstaller
)

REM ---------------------------------------------------------------------------
REM Done
REM ---------------------------------------------------------------------------
echo.
echo ============================================================
echo  Dev environment ready!
echo  Venv: %VENV_PATH%
for /f %%V in ('python -c "import sys; print(sys.version.split()[0])"') do echo  Python: %%V
for /f %%Q in ('python -c "import importlib.util; p6=importlib.util.find_spec('PyQt6'); p5=importlib.util.find_spec('PyQt5'); print('PyQt6' if p6 else 'PyQt5' if p5 else 'None') "') do echo  Qt binding: %%Q
echo ============================================================
echo.
echo To activate the environment in PowerShell:
echo   .\venv\Scripts\Activate.ps1
echo.
echo Or in Command Prompt:
echo   .\venv\Scripts\activate.bat
echo.
endlocal