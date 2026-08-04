"""Atlas | Compatibility | Qt.

Unified Qt API layer. Detects and binds to the available
Qt implementation (PyQt6 or PyQt5) at import time.

All Atlas modules must import Qt classes through this
module rather than importing directly from PyQt.

Usage::

    from atlas.compatibility.qt import QtCore
    from atlas.compatibility.qt import QtGui
    from atlas.compatibility.qt import QtWidgets
"""

# =============================================================================
# IMPORTS
# =============================================================================

import ctypes.util
import logging
import os
import sys

# =============================================================================
# LOGGING
# =============================================================================

LOGGER = logging.getLogger(__name__)

# =============================================================================
# LINUX ENVIRONMENT CONFIGURATION
# =============================================================================


def _has_xcb_cursor() -> bool:
    """Return True if libxcb-cursor is available on this system.

    Qt6's xcb platform plugin requires libxcb-cursor0 (Qt >= 6.5).
    If absent, falling back to PyQt5 avoids a hard crash on launch.

    Returns:
        bool: True if found or not running on Linux.

    """
    if not sys.platform.startswith("linux"):
        return True
    return bool(ctypes.util.find_library("xcb-cursor"))


def _configure_linux_environment() -> None:
    """Configure Qt environment variables for Linux compatibility.

    Sets QT_QPA_PLATFORM, preferring xcb on X11 sessions and
    wayland on Wayland sessions. Never overrides variables the
    user or session has already set.

    """
    if not sys.platform.startswith("linux"):
        return

    try:
        if not os.environ.get("QT_QPA_PLATFORM"):
            is_wayland = bool(
                os.environ.get("WAYLAND_DISPLAY")
                or os.environ.get("XDG_SESSION_TYPE") == "wayland"
            )
            platform = "wayland;xcb" if is_wayland else "xcb;wayland"
            os.environ["QT_QPA_PLATFORM"] = platform
            os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
            LOGGER.debug("QT_QPA_PLATFORM set to '%s'", platform)

        if not _has_xcb_cursor():
            LOGGER.warning(
                "Missing libxcb-cursor0. Install via: "
                "'sudo apt install libxcb-cursor0' (Debian/Ubuntu) or "
                "'sudo dnf install xcb-util-cursor' (Fedora/RHEL). "
                "Falling back to PyQt5 if available."
            )

    except Exception:
        LOGGER.error("Failed to configure Linux environment", exc_info=True)


_configure_linux_environment()

# =============================================================================
# QT BINDING RESOLUTION
# =============================================================================

QT_API = None
"""Name of the active Qt binding ('PyQt6' or 'PyQt5')."""

_py_ver = sys.version_info[:2]
_is_win = sys.platform == "win32"
_is_linux = sys.platform.startswith("linux")

# Selection rules:
#   Windows Python <= 3.8         -> PyQt5 first
#   Linux without libxcb-cursor   -> PyQt5 first (Qt6 xcb would crash)
#   Linux Python < 3.8            -> PyQt5 first
#   All other cases               -> PyQt6 first, PyQt5 fallback
if (_is_win and _py_ver <= (3, 8)) or (
    _is_linux and (not _has_xcb_cursor() or _py_ver < (3, 8))
):
    _primary, _secondary = "PyQt5", "PyQt6"
else:
    _primary, _secondary = "PyQt6", "PyQt5"


def _import_qt_binding(name: str):
    """Import and return (QtCore, QtGui, QtWidgets) for the given binding.

    Args:
        name (str): Either 'PyQt6' or 'PyQt5'.

    Returns:
        tuple: (QtCore, QtGui, QtWidgets).

    """
    if name == "PyQt6":
        from PyQt6 import QtCore, QtGui, QtWidgets
    else:
        from PyQt5 import QtCore, QtGui, QtWidgets
    return QtCore, QtGui, QtWidgets


try:
    QtCore, QtGui, QtWidgets = _import_qt_binding(_primary)
    QT_API = _primary
except ImportError:
    try:
        QtCore, QtGui, QtWidgets = _import_qt_binding(_secondary)
        QT_API = _secondary
    except ImportError:
        raise ImportError(
            "Atlas requires PyQt6 or PyQt5. Neither package was found."
        )

LOGGER.debug("Qt binding resolved: %s", QT_API)
