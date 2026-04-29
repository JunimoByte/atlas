"""Atlas | Packages | Themes.

Cross-platform theming system for Atlas.

Automatically applies light/dark themes on Windows.
Supports buttons, progress bars, and labels.
"""

# =============================================================================
# IMPORTS
# =============================================================================

import logging
import os
import platform
import sys

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QGuiApplication, QIcon, QPixmap
from PyQt6.QtWidgets import QLabel

# =============================================================================
# LOGGING
# =============================================================================

LOGGER = logging.getLogger(__name__)

# =============================================================================
# VARIABLES
# =============================================================================

OS = platform.system().lower()

# =============================================================================
# MAIN FUNCTIONS
# =============================================================================


def initialize(window) -> None:
    """Initialize the theming system for the application window.

    Apply the window icon, backdrop, and initial theme (light or dark).
    On Windows, also set up a listener for OS color scheme changes.

    Args:
        window (QWidget): The main application window to style.

    """
    if not window:
        LOGGER.warning("No window provided for theme initialization.")
        return

    icon(window)

    backdrop_label = window.findChild(QLabel, "Backdrop")
    if backdrop_label:
        backdrop(backdrop_label)

    apply(window)

    if OS == "windows":
        try:
            hints = QGuiApplication.styleHints()
            if hints:
                hints.colorSchemeChanged.connect(
                    lambda: QTimer.singleShot(0, lambda: apply(window))
                )
        except Exception:
            LOGGER.error("Failed to enable live theme updates", exc_info=True)


def apply(window) -> None:
    """Apply the detected system theme to the provided window.

    Detect the current OS theme (Light or Dark) and apply the
    corresponding stylesheets and window attributes.

    Args:
        window (QWidget): The main application window to style.

    """
    if not window:
        LOGGER.warning("No window provided! Skipping theme application.")
        return

    # Detect and apply theme
    theme = _get_theme()
    try:
        _apply_light(window) if theme == "Light" else _apply_dark(window)
    except Exception:
        LOGGER.error("Theme application failed", exc_info=True)


# =============================================================================
# THEME DETECTION
# =============================================================================


def _get_theme() -> str:
    """Detect current Windows theme (light/dark)."""
    if OS != "windows" or sys.getwindowsversion().major < 10:
        return "Light"

    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        ) as key:
            value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")

        return "Dark" if value == 0 else "Light"
    except Exception:
        return "Light"


# =============================================================================
# THEME APPLICATION
# =============================================================================


def _apply_light(window) -> None:
    """Apply light theme to the window."""
    if OS != "windows":
        return
    try:
        window.setStyleSheet(
            """
            QWidget#MainDialog {
                color: #000000;
                background-color: #ffffff;
            }
            """
        )
    except Exception as error:
        LOGGER.error("Failed to apply light theme: %s", error)


def _apply_dark(window) -> None:
    """Apply dark theme to the window."""
    if OS != "windows":
        return

    try:
        hwnd = int(window.winId())

        # Apply Windows dark mode attributes
        for attr in (20, 19):
            from ctypes import byref, c_int, c_void_p, sizeof, windll
            windll.dwmapi.DwmSetWindowAttribute(
                c_void_p(hwnd), c_int(attr), byref(c_int(1)), sizeof(c_int)
            )

        # Base style sheet
        style = """
            QWidget#MainDialog {
                background-color: #1e1e1e;
            }
            QMessageBox {
                background-color: #1e1e1e;
            }
            QLabel {
                color: white;
            }
        """

        # Buttons and progress bars
        button_style = """
            QPushButton {
                background-color: #333;
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.2);
                padding: 2px;
                min-width: 68px;
                min-height: 15px;
            }
            QPushButton:hover { background-color: #444; }
            QPushButton:pressed { background-color: #222; }
            QPushButton:focus { outline: none; border: 1px solid #888; }
        """

        # OS-specific adjustments
        if _is_windows_11_or_newer():
            style += button_style + "QPushButton { border-radius: 4px; }"
        else:
            style += """
                QProgressBar {
                    border: 1px solid #555;
                    background-color: #2b2b2b;
                    text-align: center;
                    color: white;
                    height: 12px;
                }
            """ + button_style

        window.setStyleSheet(style)

    except Exception:
        LOGGER.error("Failed to apply dark theme", exc_info=True)


# =============================================================================
# RESOURCE UTILITIES
# =============================================================================


def resource_path(filename: str) -> str:
    """Return the absolute path to a resource file.

    Handle path resolution for both development (local source) and
    PyInstaller frozen builds (MEIPASS).

    Args:
        filename (str): Name of the resource file.

    Returns:
        str: Absolute path to the resource.

    """
    try:
        if getattr(sys, "frozen", False):
            # PyInstaller: resources are in _MEIPASS/assets
            base_path = os.path.join(
                getattr(sys, "_MEIPASS", os.getcwd()), "assets"
            )
        else:
            # Dev: Navigate from src/atlas/lib/ to project root,
            # then to assets
            project_root = os.path.dirname(
                os.path.dirname(
                    os.path.dirname(
                        os.path.dirname(os.path.abspath(__file__))
                    )
                )
            )

            base_path = os.path.join(project_root, "assets")

        full_path = os.path.join(base_path, filename)
        return full_path

    except Exception:
        LOGGER.error(
            "Failed to resolve resource path for '%s'", filename, exc_info=True
        )
        return filename  # fallback, may fail gracefully


# =============================================================================
# WINDOWS UTILITIES
# =============================================================================


def _is_windows_11_or_newer() -> bool:
    """Return True if running on Windows 11 or newer.

    Use the build number from sys.getwindowsversion().
    """
    if OS != "windows":
        return False
    try:
        ver = sys.getwindowsversion()
        return ver.major >= 10 and ver.build >= 22000
    except Exception:
        return False


# =============================================================================
# IMAGE UTILITIES
# =============================================================================


def backdrop(element) -> None:
    """Set a backdrop image to a widget.

    Load 'images/Backdrop.png' from resources and scale it to fill
    the element.

    Args:
        element (QLabel): The widget to apply the backdrop to.

    """
    try:
        image_path = resource_path("images/Backdrop.png")

        if not os.path.exists(image_path):
            LOGGER.warning("Backdrop image not found: %s", image_path)
            return

        element.setPixmap(QPixmap(image_path))
        element.setScaledContents(True)

        LOGGER.debug("Backdrop set successfully: %s", image_path)

    except Exception as error:
        LOGGER.error("Failed to set backdrop: %s", error)


def icon(window) -> None:
    """Set the application window icon.

    Load 'icons/Icon.ico' from resources and apply it to the window.

    Args:
        window (QWidget): The window to set the icon for.

    """
    try:
        icon_path = resource_path("icons/Icon.ico")

        if not os.path.exists(icon_path):
            LOGGER.warning("Icon file not found: %s", icon_path)
            return

        window.setWindowIcon(QIcon(icon_path))
        LOGGER.debug("Window icon set successfully: %s", icon_path)

    except Exception as error:
        LOGGER.error("Failed to set window icon: %s", error)
