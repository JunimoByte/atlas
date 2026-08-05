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


def _configure_frozen_linux_environment() -> None:
    """Suppress GIO module conflicts when running as a frozen binary.

    PyInstaller bundles GLib from the build system (Ubuntu 20.04). On
    newer distros (Ubuntu 22.04+), GIO tries to load system modules
    compiled against a newer GLib, producing ``undefined symbol``
    errors. Setting ``GIO_MODULE_DIR`` to an empty string prevents GIO
    from searching the system module directory entirely.

    ``NO_AT_BRIDGE`` silences the ATK accessibility-bridge signature
    mismatch warning that appears on GNOME 46+ desktops.

    Only applied when the process is a frozen PyInstaller build so
    development runs are unaffected.

    """
    if not sys.platform.startswith("linux"):
        return
    if not getattr(sys, "frozen", False):
        return

    try:
        os.environ.setdefault("GIO_MODULE_DIR", "")
        os.environ.setdefault("NO_AT_BRIDGE", "1")
        LOGGER.debug(
            "Frozen Linux: GIO_MODULE_DIR and NO_AT_BRIDGE suppressed."
        )
    except Exception:
        LOGGER.error(
            "Failed to configure frozen Linux environment", exc_info=True
        )


def _configure_linux_environment() -> None:
    """Configure the Qt platform backend for Linux.

    Forces Qt to use the xcb (X11/XWayland) backend on Linux so that
    GNOME's Wayland compositor (Mutter) does not override window flags
    with its own Client-Side Decorations. XWayland is available on all
    Ubuntu 22.04 LTS+ and equivalent systems, making this safe.

    The variable is only set if the user has not already defined it,
    so explicit overrides from the shell are always respected.

    """
    if not sys.platform.startswith("linux"):
        return

    try:
        if not os.environ.get("QT_QPA_PLATFORM"):
            os.environ["QT_QPA_PLATFORM"] = "xcb"
            LOGGER.debug("QT_QPA_PLATFORM forced to 'xcb' for Linux.")
    except Exception:
        LOGGER.error(
            "Failed to configure Linux environment", exc_info=True
        )


_configure_frozen_linux_environment()
_configure_linux_environment()

# =============================================================================
# QT BINDING RESOLUTION
# =============================================================================

QT_API = None
"""Name of the active Qt binding ('PyQt6' or 'PyQt5')."""

try:
    from PyQt6 import QtCore, QtGui, QtWidgets

    QT_API = "PyQt6"
except ImportError:
    try:
        # Shadowing the PyQt6 names above is intentional: whichever
        # branch succeeds exports QtCore/QtGui/QtWidgets to callers.
        from PyQt5 import QtCore, QtGui, QtWidgets  # noqa: F401

        QT_API = "PyQt5"
    except ImportError:
        raise ImportError(
            "Atlas requires PyQt6 or PyQt5. Neither package was found."
        )

LOGGER.debug("Qt binding resolved: %s", QT_API)
