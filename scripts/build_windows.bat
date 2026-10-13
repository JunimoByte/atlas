@echo off
REM ============================================================================
REM Atlas - Windows Release Packaging Script
REM
REM  - Builds portable executable using PyInstaller (main.spec)
REM  - Optionally compiles Inno Setup installer (installer\Atlas.iss)
REM  - 100% compatible with Windows 7, 8, 8.1, 10, and 11
REM ============================================================================

setlocal EnableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "PROJECT_ROOT=%%~fI"

echo ============================================================
echo   Atlas Windows Release Builder
echo ============================================================
echo Project root: %PROJECT_ROOT%
echo.

REM ---------------------------------------------------------------------------
REM 1. Activate virtual environment if present
REM ---------------------------------------------------------------------------
if exist "%PROJECT_ROOT%\venv\Scripts\activate.bat" (
    echo Activating virtual environment (%PROJECT_ROOT%\venv^)...
    call "%PROJECT_ROOT%\venv\Scripts\activate.bat"
) else if exist "%PROJECT_ROOT%\.venv\Scripts\activate.bat" (
    echo Activating virtual environment (%PROJECT_ROOT%\.venv^)...
    call "%PROJECT_ROOT%\.venv\Scripts\activate.bat"
)

REM ---------------------------------------------------------------------------
REM 2. Verify Python and PyInstaller availability
REM ---------------------------------------------------------------------------
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not available on PATH or in venv.
    echo Please install Python 3.8+ or run scripts\setup_dev.bat first.
    exit /b 1
)

python -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo ERROR: PyInstaller is not installed in the current Python environment.
    echo Please install it using: pip install "pyinstaller>=6.0"
    exit /b 1
)

REM ---------------------------------------------------------------------------
REM 3. Compile standalone portable executable with PyInstaller
REM ---------------------------------------------------------------------------
echo.
echo Building portable executable with PyInstaller...
cd /d "%PROJECT_ROOT%"
python -m PyInstaller main.spec --noconfirm --clean
if errorlevel 1 (
    echo.
    echo ERROR: PyInstaller compilation failed.
    exit /b 1
)

REM Verify output executable in dist\
set "PORTABLE_EXE="
if exist "%PROJECT_ROOT%\dist\Atlas-x86_64-Portable.exe" (
    set "PORTABLE_EXE=%PROJECT_ROOT%\dist\Atlas-x86_64-Portable.exe"
) else if exist "%PROJECT_ROOT%\dist\Atlas-x86-Portable.exe" (
    set "PORTABLE_EXE=%PROJECT_ROOT%\dist\Atlas-x86-Portable.exe"
)

if "%PORTABLE_EXE%"=="" (
    echo.
    echo ERROR: Expected portable executable was not found in dist\.
    exit /b 1
)

echo.
echo [OK] Portable executable built:
echo      %PORTABLE_EXE%

REM ---------------------------------------------------------------------------
REM 4. Check for Inno Setup compiler (ISCC.exe)
REM ---------------------------------------------------------------------------
set "ISCC_CMD="

REM Check PATH first
where iscc >nul 2>&1
if not errorlevel 1 (
    set "ISCC_CMD=iscc"
) else if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
    set "ISCC_CMD=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
) else if exist "C:\Program Files\Inno Setup 6\ISCC.exe" (
    set "ISCC_CMD=C:\Program Files\Inno Setup 6\ISCC.exe"
) else if exist "C:\Program Files (x86)\Inno Setup 5\ISCC.exe" (
    set "ISCC_CMD=C:\Program Files (x86)\Inno Setup 5\ISCC.exe"
) else if exist "C:\Program Files\Inno Setup 5\ISCC.exe" (
    set "ISCC_CMD=C:\Program Files\Inno Setup 5\ISCC.exe"
)

if not "%ISCC_CMD%"=="" (
    echo.
    echo Compiling Inno Setup installer using %ISCC_CMD%...
    "%ISCC_CMD%" "%PROJECT_ROOT%\installer\Atlas.iss"
    if errorlevel 1 (
        echo WARNING: Inno Setup compilation returned an error.
    ) else (
        echo.
        echo [OK] Inno Setup installer compiled successfully in dist\
    )
) else (
    echo.
    echo NOTE: Inno Setup compiler (ISCC.exe) was not found.
    echo       To build the setup installer (.exe), install Inno Setup 5 or 6,
    echo       or open installer\Atlas.iss in the Inno Setup IDE and click Compile.
)

echo.
echo ============================================================
echo   Windows build completed successfully!
echo ============================================================
echo.

endlocal
exit /b 0
