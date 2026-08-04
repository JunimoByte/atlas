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

    Sets QT_QPA_PLATFORM for Wayland/X11 fallback and, crucially,
    sets QT_QPA_PLATFORMTHEME so Qt loads the correct native desktop
    integration plugin. This must run before QApplication is created.

    The platform theme plugin determines whether Qt can read the
    user's dark/light mode preference from the DE. Without it,
    QStyleHints.colorScheme() returns Unknown on most Linux DEs.

    Plugin mapping:
        KDE Plasma  -> kde      (reads KDE color scheme directly)
        GNOME       -> gnome    (reads GNOME/GTK color-scheme via D-Bus)
        XFCE        -> xdgdesktopportal (uses XDG portal, most compatible)
        Other/None  -> xdgdesktopportal (works on any modern compositor)

    If the user or session has already set these variables, we
    never override them.

    """
    if not sys.platform.startswith("linux"):
        return

    try:
        # --- Wayland / X11 platform fallback ---
        if not os.environ.get("QT_QPA_PLATFORM"):
            os.environ["QT_QPA_PLATFORM"] = "wayland;xcb"
            os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
            LOGGER.debug("QT_QPA_PLATFORM set to 'wayland;xcb'")

        # --- Platform theme plugin (drives dark/light detection) ---
        if not os.environ.get("QT_QPA_PLATFORMTHEME"):
            desktop = (
                os.environ.get("XDG_CURRENT_DESKTOP", "")
                .upper()
                .split(":")
            )

            if "KDE" in desktop:
                # KDE ships its own 'kde' platform theme plugin that
                # reads ~/.config/kdeglobals and the Plasma color scheme.
                theme_plugin = "kde"
            elif "GNOME" in desktop or "UNITY" in desktop:
                # The 'gnome' plugin reads
                # org.gnome.desktop.interface color-scheme via D-Bus.
                # qgnomeplatform provides this; falls back gracefully
                # if not installed.
                theme_plugin = "gnome"
            else:
                # For XFCE, LXQt, Cinnamon, Mate, tiling WMs, etc.
                # xdgdesktopportal queries org.freedesktop.portal.Settings
                # (the modern cross-DE standard supported by
                # xdg-desktop-portal-gtk and xdg-desktop-portal-kde).
                theme_plugin = "xdgdesktopportal"

            os.environ["QT_QPA_PLATFORMTHEME"] = theme_plugin
            LOGGER.debug(
                "QT_QPA_PLATFORMTHEME set to '%s' for desktop '%s'",
                theme_plugin,
                ":".join(desktop) or "(undetected)",
            )

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

try:
    from PyQt6 import QtCore, QtGui, QtWidgets

    QT_API = "PyQt6"
except ImportError:
    try:
        from PyQt5 import QtCore, QtGui, QtWidgets  # noqa: F401

        QT_API = "PyQt5"
    except ImportError:
        raise ImportError(
            "Atlas requires PyQt6 or PyQt5. " "Neither package was found."
        )

LOGGER.debug("Qt binding resolved: %s", QT_API)
