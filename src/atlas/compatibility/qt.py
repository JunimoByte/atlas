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


def _configure_linux_environment() -> None:
    """Configure Qt environment variables for Linux compatibility.

    Sets QT_QPA_PLATFORM for Wayland/X11 fallback. If the user or
    session has already set these variables, we never override them.

    """
    if not sys.platform.startswith("linux"):
        return

    try:
        # --- Wayland / X11 platform fallback ---
        if not os.environ.get("QT_QPA_PLATFORM"):
            os.environ["QT_QPA_PLATFORM"] = "wayland;xcb"
            os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
            LOGGER.debug("QT_QPA_PLATFORM set to 'wayland;xcb'")

    except Exception:
        LOGGER.error(
            "Failed to configure Linux environment",
            exc_info=True,
        )


_configure_linux_environment()

# =============================================================================
# QT BINDING RESOLUTION
# =============================================================================

QT_API = None
"""Name of the active Qt binding ('PyQt6' or 'PyQt5')."""

_is_win = sys.platform == "win32"
_is_linux = sys.platform.startswith("linux")
_py_ver = sys.version_info[:2]

# Binding resolution preferences:
# - Windows with Python 3.8 or older -> fallback to PyQt5
# - Linux with Python 3.8 or newer -> use PyQt6, else fallback to PyQt5
if (_is_win and _py_ver <= (3, 8)) or (_is_linux and _py_ver < (3, 8)):
    _primary, _secondary = "PyQt5", "PyQt6"
else:
    _primary, _secondary = "PyQt6", "PyQt5"


def _import_qt_binding(binding_name: str):
    """Import QtCore, QtGui, QtWidgets for specified binding name.

    Args:
        binding_name (str): 'PyQt6' or 'PyQt5'.

    Returns:
        tuple: (QtCore, QtGui, QtWidgets).

    """
    if binding_name == "PyQt6":
        from PyQt6 import QtCore, QtGui, QtWidgets

        return QtCore, QtGui, QtWidgets
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
