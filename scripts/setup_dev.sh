#!/usr/bin/env bash
# =============================================================================
# Atlas dev environment setup — Linux / macOS / BSD
#
#  Usage:  source scripts/setup_dev.sh   (from the project root)
#
#  - Creates/reuses a venv in the project root
#  - Installs dev tools (pytest, black, flake8, ruff where available)
#  - Installs Qt binding (pip on Linux/macOS; system pkg on BSD)
#  - Installs PyInstaller
# =============================================================================



# -----------------------------------------------------------------------------
# SHELL GUARD — must be bash or zsh
# -----------------------------------------------------------------------------
if [ -z "${BASH_VERSION:-}" ] && [ -z "${ZSH_VERSION:-}" ]; then
    echo "ERROR: Run this script in bash or zsh: source scripts/setup_dev.sh"
    return 1 2>/dev/null || exit 1
fi

# -----------------------------------------------------------------------------
# SOURCE GUARD — must be sourced, not executed
# Sourcing keeps the venv activation in the caller's shell.
# BASH_SOURCE is empty in zsh, so each shell gets its own check.
# -----------------------------------------------------------------------------
_is_sourced=0
if [[ -n "${BASH_VERSION:-}" ]]; then
    [[ "${BASH_SOURCE[0]}" != "${0}" ]] && _is_sourced=1
elif [[ -n "${ZSH_VERSION:-}" ]]; then
    [[ "${ZSH_EVAL_CONTEXT:-}" == *:file:* || \
       "${ZSH_EVAL_CONTEXT:-}" == *:file  ]] && _is_sourced=1
fi
if [[ "$_is_sourced" == "0" ]]; then
    echo "ERROR: This script must be sourced, not executed directly."
    echo "       Run: source scripts/setup_dev.sh"
    exit 1
fi

# -----------------------------------------------------------------------------
# PATH RESOLUTION — bash and zsh compatible
# BASH_SOURCE[0] is empty in zsh; ${(%):-%x} gives the sourced file path.
# -----------------------------------------------------------------------------
if [[ -n "${BASH_VERSION:-}" ]]; then
    _SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
elif [[ -n "${ZSH_VERSION:-}" ]]; then
    # shellcheck disable=SC2296
    _SCRIPT_DIR="$(cd "$(dirname "${(%):-%x}")" && pwd)"
else
    echo "ERROR: Cannot determine script directory." >&2
    return 1
fi
PROJECT_ROOT="$(cd "$_SCRIPT_DIR/.." && pwd)"
VENV_PATH="$PROJECT_ROOT/venv"

# -----------------------------------------------------------------------------
# HELPERS
# -----------------------------------------------------------------------------

is_bsd() {
    [[ "$OSTYPE" == freebsd*   || "$OSTYPE" == openbsd* || \
       "$OSTYPE" == netbsd*    || "$OSTYPE" == dragonfly* ]]
}

run_privileged() {
    # Run a command as root, using sudo when not already root.
    if [ "$(id -u)" -eq 0 ]; then
        "$@"
    elif command -v sudo >/dev/null 2>&1; then
        sudo "$@"
    else
        echo "ERROR: root or sudo required." >&2
        return 1
    fi
}

# -----------------------------------------------------------------------------
# LINUX — XCB / XWAYLAND RUNTIME LIBRARIES
# Required for the Qt XCB platform plugin used by PyInstaller builds.
# Skipped automatically on macOS and BSD.
# -----------------------------------------------------------------------------

_XCB_LIBS=(
    "libxcb-cursor.so.0"
    "libxcb-icccm.so.4"
    "libxcb-image.so.0"
    "libxcb-keysyms.so.1"
    "libxcb-render-util.so.0"
    "libxcb-xkb.so.1"
    "libxkbcommon-x11.so.0"
)

_has_xcb_libraries() {
    command -v ldconfig >/dev/null 2>&1 || return 1
    local lib
    for lib in "${_XCB_LIBS[@]}"; do
        ldconfig -p 2>/dev/null | grep -Fq "$lib" || return 1
    done
}

_print_missing_xcb() {
    echo "Missing XCB/XWayland libraries:"
    local lib
    for lib in "${_XCB_LIBS[@]}"; do
        ldconfig -p 2>/dev/null | grep -Fq "$lib" || echo "  - $lib"
    done
}

_install_xcb_libraries() {
    local deb_pkgs=(
        libxcb-cursor0 libxcb-icccm4 libxcb-image0 libxcb-keysyms1
        libxcb-render-util0 libxcb-xkb1 libxkbcommon-x11-0
    )
    local gen_pkgs=(
        libxcb libxkbcommon-x11 xcb-util-cursor xcb-util-image
        xcb-util-keysyms xcb-util-renderutil xcb-util-wm
    )

    if   command -v apt-get   >/dev/null 2>&1; then
        run_privileged apt-get update
        run_privileged apt-get install -y "${deb_pkgs[@]}"
    elif command -v dnf       >/dev/null 2>&1; then
        run_privileged dnf install -y "${gen_pkgs[@]}"
    elif command -v yum       >/dev/null 2>&1; then
        run_privileged yum install -y "${gen_pkgs[@]}"
    elif command -v pacman    >/dev/null 2>&1; then
        run_privileged pacman -S --needed --noconfirm libxkbcommon "${gen_pkgs[@]}"
    elif command -v zypper    >/dev/null 2>&1; then
        run_privileged zypper --non-interactive install \
            libxcb1 libxkbcommon-x11-0 \
            xcb-util-cursor xcb-util-image xcb-util-keysyms \
            xcb-util-renderutil xcb-util-wm
    elif command -v apk       >/dev/null 2>&1; then
        run_privileged apk add libxkbcommon "${gen_pkgs[@]}"
    elif command -v xbps-install >/dev/null 2>&1; then
        run_privileged xbps-install -y libxkbcommon "${gen_pkgs[@]}"
    elif command -v slackpkg  >/dev/null 2>&1; then
        run_privileged slackpkg -batch=on -default_answer=y install \
            libxkbcommon "${gen_pkgs[@]}"
    else
        echo "ERROR: No supported Linux package manager found."
        echo "       Install the XCB libraries manually, then re-run setup."
        return 1
    fi
}

setup_linux_xcb() {
    # No-op on non-Linux systems.
    [[ "$OSTYPE" == linux* ]] || return 0

    if _has_xcb_libraries; then
        echo "XCB/XWayland libraries already installed."
        return 0
    fi

    echo ""
    echo "Atlas requires XCB/XWayland runtime libraries for reliable Qt startup."
    printf "Install them now? [Y/n] "
    local response
    read -r response
    case "${response:-Y}" in
        Y|y|YES|yes|Yes) _install_xcb_libraries ;;
        *) echo "Setup stopped: XCB libraries declined."; return 1 ;;
    esac

    if ! _has_xcb_libraries; then
        echo "ERROR: XCB library installation incomplete."
        _print_missing_xcb
        return 1
    fi
    echo "XCB/XWayland libraries installed."
}

# -----------------------------------------------------------------------------
# BSD — find the Python version that has PyQt in the pkg repo
# Returns the python binary name (e.g. "python3.12") or falls back to python3.
# -----------------------------------------------------------------------------
_bsd_pyqt_python() {
    local pyqt_pkg
    pyqt_pkg=$(pkg search -q "qt6-pyqt" 2>/dev/null \
        | grep -E "^py[0-9]+-qt6-pyqt" | sort -V | tail -n 1) || true

    if [[ -z "$pyqt_pkg" ]]; then
        echo "python3"
        return
    fi

    local ver_flat ver_dot
    ver_flat=$(echo "$pyqt_pkg" | grep -oE "^py[0-9]+" | tr -d 'py') || true
    ver_dot="${ver_flat:0:1}.${ver_flat:1}"
    echo "python${ver_dot}"
}

# -----------------------------------------------------------------------------
# STEP 1 — Virtual environment
# -----------------------------------------------------------------------------
setup_venv() {
    if [ -f "$VENV_PATH/bin/activate" ]; then
        echo "Existing virtual environment found."
        return 0
    fi

    echo "Creating virtual environment..."

    if is_bsd; then
        # Use the Python version that matches the pkg PyQt binaries so
        # --system-site-packages can actually see them.
        local py_bin
        py_bin=$(_bsd_pyqt_python)
        if ! command -v "$py_bin" >/dev/null 2>&1; then
            echo "ERROR: $py_bin not found. Install the matching Python via pkg."
            return 1 2>/dev/null || exit 1
        fi
        echo "Using $py_bin (matches pkg PyQt version)."
        "$py_bin" -m venv --system-site-packages "$VENV_PATH"
    else
        python3 -m venv "$VENV_PATH" || {
            echo "ERROR: Failed to create venv. Install python3-venv and retry."
            return 1 2>/dev/null || exit 1
        }
    fi
}

# -----------------------------------------------------------------------------
# STEP 2 — Activate
# -----------------------------------------------------------------------------
activate_venv() {
    echo "Activating virtual environment..."
    # shellcheck disable=SC1091
    source "$VENV_PATH/bin/activate"
}

# -----------------------------------------------------------------------------
# STEP 3 — Upgrade pip
# -----------------------------------------------------------------------------
upgrade_pip() {
    echo "Upgrading pip..."
    python -m pip install --upgrade pip --quiet
}

# -----------------------------------------------------------------------------
# STEP 4 — Dev tools  (pytest, black, flake8, ruff where supported)
# Use a temp variable: zsh interprets "$VAR[dev]" as array subscripting,
# expanding to empty string and causing pip to fail with a blank requirement.
# -----------------------------------------------------------------------------
install_dev_tools() {
    echo "Installing dev tools..."
    local target="${PROJECT_ROOT}[dev]"
    python -m pip install --quiet -e "$target" || {
        echo "ERROR: Failed to install dev dependencies."
        return 1 2>/dev/null || exit 1
    }
}

# -----------------------------------------------------------------------------
# STEP 5 — Qt binding
# Linux/macOS: install via pip (PyQt6 first, PyQt5 fallback).
# BSD:         PyQt cannot be compiled from source by pip — it must come from
#              the system package manager (pkg). Verify it is visible, and
#              print actionable instructions if it is not.
# -----------------------------------------------------------------------------
install_qt_binding() {
    echo "Installing Qt binding..."

    if is_bsd; then
        _install_qt_bsd
    else
        _install_qt_pip
    fi
}

_install_qt_pip() {
    if ! python -m pip install --quiet "PyQt6>=6.0"; then
        echo "PyQt6 unavailable, trying PyQt5..."
        python -m pip install --quiet "PyQt5>=5.15" || {
            echo "ERROR: Failed to install PyQt5 fallback."
            return 1 2>/dev/null || exit 1
        }
    fi
}

_install_qt_bsd() {
    # PyQt is already importable (system-site-packages picked it up).
    if python -c "import PyQt6.QtCore" 2>/dev/null || \
       python -c "import PyQt5.QtCore" 2>/dev/null; then
        echo "PyQt detected from system packages."
        return 0
    fi

    # Not importable — diagnose and guide the user.
    local py_ver py_dot
    py_ver=$(python -c 'import sys; v=sys.version_info; print(f"{v.major}{v.minor}")')
    py_dot=$(python -c 'import sys; v=sys.version_info; print(f"{v.major}.{v.minor}")')

    local qt_pkg pytest_pkg repo_ver repo_dot
    qt_pkg=$(pkg search -q "qt6-pyqt" 2>/dev/null \
        | grep -E "^py[0-9]+-qt6-pyqt" | sort -V | tail -n 1) || true
    pytest_pkg=$(pkg search -q "pytest-qt" 2>/dev/null \
        | grep -E "^py[0-9]+-pytest-qt" | sort -V | tail -n 1) || true

    echo "ERROR: PyQt not visible in this environment (Python $py_dot)."
    echo "BSD has no pip wheels for PyQt — use the system package manager."
    echo ""

    if [[ -n "$qt_pkg" ]]; then
        repo_ver=$(echo "$qt_pkg" | grep -oE "^py[0-9]+" | tr -d 'py') || true
        repo_dot="${repo_ver:0:1}.${repo_ver:1}"
        echo "Your pkg repo provides PyQt for Python $repo_dot:"
        echo "    sudo pkg install $qt_pkg${pytest_pkg:+ $pytest_pkg}"
        echo ""
        if [[ "$py_ver" != "$repo_ver" ]]; then
            echo "Your venv is Python $py_dot but pkg only has PyQt for Python $repo_dot."
            echo "Recreate the venv with the correct Python version:"
            echo ""
            echo "    rm -rf \"$VENV_PATH\""
            echo "    source \"$PROJECT_ROOT/scripts/setup_dev.sh\""
        else
            echo "After installing, re-run:"
            echo "    source \"$PROJECT_ROOT/scripts/setup_dev.sh\""
        fi
    else
        echo "Could not find a PyQt package in your repositories."
        echo "Try: pkg search qt6-pyqt"
        echo "Then install it and re-run: source \"$PROJECT_ROOT/scripts/setup_dev.sh\""
    fi

    return 1 2>/dev/null || exit 1
}

# -----------------------------------------------------------------------------
# STEP 6 — PyInstaller
# -----------------------------------------------------------------------------
install_pyinstaller() {
    echo "Installing PyInstaller..."
    python -m pip install --quiet "pyinstaller>=6.0" || {
        echo "WARNING: PyInstaller installation failed."
        echo "         Install manually: pip install pyinstaller"
    }
}

# -----------------------------------------------------------------------------
# SUMMARY
# -----------------------------------------------------------------------------
print_summary() {
    echo ""
    echo "============================================================"
    echo " Dev environment ready!"
    echo " Venv:   $VENV_PATH"
    python -c "import sys; print(' Python: ' + sys.version.split()[0])"
    python -c "
try:
    import PyQt6.QtCore
    print(' Qt:     PyQt6', PyQt6.QtCore.PYQT_VERSION_STR)
except ImportError:
    try:
        import PyQt5.QtCore
        print(' Qt:     PyQt5', PyQt5.QtCore.PYQT_VERSION_STR)
    except ImportError:
        pass
"
    echo "============================================================"
    echo ""
}

# =============================================================================
# MAIN
# =============================================================================
setup_linux_xcb   || { return 1 2>/dev/null || exit 1; }
setup_venv        || { return 1 2>/dev/null || exit 1; }
activate_venv
upgrade_pip
install_dev_tools || { return 1 2>/dev/null || exit 1; }
install_qt_binding
install_pyinstaller
print_summary
