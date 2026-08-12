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
# LINUX XCB / XWAYLAND DEPENDENCIES
# ---------------------------------------------------------------------------

XCB_LIBRARIES=(
    "libxcb-cursor.so.0"
    "libxcb-icccm.so.4"
    "libxcb-image.so.0"
    "libxcb-keysyms.so.1"
    "libxcb-render-util.so.0"
    "libxcb-xkb.so.1"
    "libxkbcommon-x11.so.0"
)


has_xcb_libraries() {
    # Return success when all required XCB libraries are available.
    local library

    if ! command -v ldconfig >/dev/null 2>&1; then
        return 1
    fi

    for library in "${XCB_LIBRARIES[@]}"; do
        if ! ldconfig -p 2>/dev/null | grep -Fq "$library"; then
            return 1
        fi
    done

    return 0
}


print_missing_xcb_libraries() {
    # Print the XCB libraries unavailable on the current system.
    local library

    echo "Missing XCB/XWayland libraries:"
    for library in "${XCB_LIBRARIES[@]}"; do
        if ! ldconfig -p 2>/dev/null | grep -Fq "$library"; then
            echo "  - $library"
        fi
    done
}


run_privileged() {
    # Run a package command as root through sudo when necessary.
    if [ "$(id -u)" -eq 0 ]; then
        "$@"
        return
    fi

    if command -v sudo >/dev/null 2>&1; then
        sudo "$@"
        return
    fi

    echo "ERROR: Root access or sudo is required to install XCB libraries."
    return 1
}


install_xcb_libraries() {
    # Install XCB/XWayland runtime libraries with the available manager.
    local debian_packages=(
        libxcb-cursor0
        libxcb-icccm4
        libxcb-image0
        libxcb-keysyms1
        libxcb-render-util0
        libxcb-xkb1
        libxkbcommon-x11-0
    )
    local general_packages=(
        libxcb
        libxkbcommon-x11
        xcb-util-cursor
        xcb-util-image
        xcb-util-keysyms
        xcb-util-renderutil
        xcb-util-wm
    )

    if command -v apt-get >/dev/null 2>&1; then
        run_privileged apt-get update
        run_privileged apt-get install -y "${debian_packages[@]}"
    elif command -v dnf >/dev/null 2>&1; then
        run_privileged dnf install -y "${general_packages[@]}"
    elif command -v yum >/dev/null 2>&1; then
        run_privileged yum install -y "${general_packages[@]}"
    elif command -v pacman >/dev/null 2>&1; then
        run_privileged pacman -S --needed --noconfirm \
            libxkbcommon "${general_packages[@]}"
    elif command -v zypper >/dev/null 2>&1; then
        run_privileged zypper --non-interactive install \
            libxcb1 libxkbcommon-x11-0 \
            xcb-util-cursor xcb-util-image xcb-util-keysyms \
            xcb-util-renderutil xcb-util-wm
    elif command -v apk >/dev/null 2>&1; then
        run_privileged apk add libxkbcommon "${general_packages[@]}"
    elif command -v xbps-install >/dev/null 2>&1; then
        run_privileged xbps-install -y libxkbcommon "${general_packages[@]}"
    elif command -v slackpkg >/dev/null 2>&1; then
        run_privileged slackpkg -batch=on -default_answer=y install \
            libxkbcommon "${general_packages[@]}"
    else
        echo "ERROR: No supported Linux package manager was detected."
        echo "Install the missing XCB libraries manually, then rerun setup."
        return 1
    fi
}


ensure_linux_xcb_libraries() {
    # Prompt for and verify Linux XCB/XWayland runtime dependencies.
    local response

    if [[ "$OSTYPE" != linux* ]]; then
        return 0
    fi

    if has_xcb_libraries; then
        echo "XCB/XWayland compatibility libraries are already installed."
        return 0
    fi

    echo ""
    echo "Atlas requires XCB/XWayland runtime libraries for reliable Qt startup."
    echo "This includes libxcb-cursor and related XCB libraries."
    echo "Skipping installation can result in a portable build that fails to"
    echo "start on Linux systems."
    printf "Install the required compatibility libraries now? [Y/n] "
    read -r response

    case "${response:-Y}" in
        Y|y|YES|yes|Yes)
            install_xcb_libraries
            ;;
        *)
            echo "Setup stopped: required XCB/XWayland libraries were declined."
            return 1
            ;;
    esac

    if ! has_xcb_libraries; then
        echo "ERROR: XCB/XWayland library installation did not complete."
        print_missing_xcb_libraries
        return 1
    fi

    echo "XCB/XWayland compatibility libraries installed successfully."
}


if ! ensure_linux_xcb_libraries; then
    return 1 2>/dev/null || exit 1
fi

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
# 5. Install Qt binding — try PyQt6 first, fall back to PyQt5
# ---------------------------------------------------------------------------
echo "Installing Qt binding..."
if ! python -m pip install --quiet "PyQt6>=6.0"; then
    echo "PyQt6 failed, falling back to PyQt5..."
    python -m pip install --quiet "PyQt5>=5.15" || {
        echo "ERROR: Failed to install PyQt5 fallback."
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
echo "Setup complete."
echo ""
echo "To activate the environment in your current shell run:"
echo "   source $VENV_PATH/bin/activate"
echo ""
