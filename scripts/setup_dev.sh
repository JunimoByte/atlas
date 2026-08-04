#!/usr/bin/env bash
# ============================================================================
# Atlas dev environment setup (Linux/macOS)
#
#  - Creates/reuses a venv in the project root
#  - Installs dev tools (pytest, ruff, black, flake8)
#  - Auto-detects Python version and installs PyQt6 (Python 3.9+) or PyQt5
#  - Installs PyInstaller for building portable executables
# ============================================================================

set -e  # Exit immediately if a command fails

# Ensure we are running in bash/zsh
if [ -z "$BASH_VERSION" ] && [ -z "$ZSH_VERSION" ]; then
    echo "Please run this script in bash or zsh:"
    echo "   source scripts/setup_dev.sh"
    return 1 2>/dev/null || exit 1
fi

# Get the project root (parent folder of this script)
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_PATH="$PROJECT_ROOT/venv"

# ---------------------------------------------------------------------------
# 1. Create venv if it doesn't exist
# ---------------------------------------------------------------------------
if [ -f "$VENV_PATH/bin/activate" ]; then
    echo "Existing virtual environment found."
else
    echo "Creating new virtual environment in project root..."
    python3 -m venv "$VENV_PATH" || {
        echo "ERROR: Failed to create virtual environment."
        echo "Make sure python3-venv is installed."
        return 1 2>/dev/null || exit 1
    }
fi

# ---------------------------------------------------------------------------
# 2. Activate
# ---------------------------------------------------------------------------
echo "Activating virtual environment..."
# shellcheck disable=SC1091
source "$VENV_PATH/bin/activate"

# ---------------------------------------------------------------------------
# 3. Upgrade pip
# ---------------------------------------------------------------------------
echo "Upgrading pip..."
python -m pip install --upgrade pip --quiet

# ---------------------------------------------------------------------------
# 4. Install dev tools
# ---------------------------------------------------------------------------
echo "Installing dev tools..."
python -m pip install --quiet -e "$PROJECT_ROOT[dev]" || {
    echo "ERROR: Failed to install dev dependencies."
    return 1 2>/dev/null || exit 1
}

# ---------------------------------------------------------------------------
# 5. Detect Python version and install the correct Qt binding
# ---------------------------------------------------------------------------
echo "Detecting Python version for Qt binding selection..."
PY_MINOR=$(python -c "import sys; print(sys.version_info.minor)")

if [ "$PY_MINOR" -ge 9 ]; then
    echo "Python 3.$PY_MINOR detected -- installing PyQt6..."
    if ! python -m pip install --quiet "PyQt6>=6.4"; then
        echo "PyQt6 failed, falling back to PyQt5..."
        python -m pip install --quiet "PyQt5>=5.15" || {
            echo "ERROR: Failed to install PyQt5 fallback."
            return 1 2>/dev/null || exit 1
        }
    fi
else
    echo "Python 3.$PY_MINOR detected -- installing PyQt5 for compatibility..."
    python -m pip install --quiet "PyQt5>=5.15" || {
        echo "ERROR: Failed to install PyQt5."
        return 1 2>/dev/null || exit 1
    }
fi

# ---------------------------------------------------------------------------
# 6. Install PyInstaller
# ---------------------------------------------------------------------------
echo "Installing PyInstaller..."
python -m pip install --quiet "pyinstaller>=6.0" || {
    echo "WARNING: PyInstaller installation failed."
    echo "You can install it manually: pip install pyinstaller"
}

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
echo ""
echo "============================================================"
echo " Dev environment ready!"
echo " Venv: $VENV_PATH"
python -c "import sys; print(' Python: ' + sys.version.split()[0])"
python -c "try:
  import PyQt6.QtCore; print(' Qt binding: PyQt6', PyQt6.QtCore.PYQT_VERSION_STR)
except:
  try:
    import PyQt5.QtCore; print(' Qt binding: PyQt5', PyQt5.QtCore.PYQT_VERSION_STR)
  except:
    pass"
echo "============================================================"
echo ""
echo "Your venv is now active in this shell."