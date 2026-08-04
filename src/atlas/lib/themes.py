"""Atlas | Packages | Themes.

Theme detection and application for Atlas.

On Windows: reads the registry and applies stylesheets + DWM
titlebar colouring for light and dark modes.
On all other platforms: theme detection is delegated to Qt style
hints and the system palette; no stylesheets are applied, so the
native DE theme is used as-is.
"""

# =============================================================================
# IMPORTS
# =============================================================================

import logging
import os
import sys

from atlas.compatibility.qt import QtCore, QtGui, QtWidgets

# =============================================================================
# LOGGING
# =============================================================================

LOGGER = logging.getLogger(__name__)

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

    backdrop_label = window.findChild(QtWidgets.QLabel, "Backdrop")
    if backdrop_label:
        backdrop(backdrop_label)

    apply(window)

    # Wire live theme-change listener if the Qt version supports it.
    # colorSchemeChanged was added in Qt 6.5; gracefully skip on older
    # versions and on platforms where the signal is absent.
    try:
        hints = QtGui.QGuiApplication.styleHints()
        if hints and hasattr(hints, "colorSchemeChanged"):
            hints.colorSchemeChanged.connect(
                lambda: QtCore.QTimer.singleShot(0, lambda: apply(window))
            )
        else:
            LOGGER.debug(
                "colorSchemeChanged unavailable; "
                "live theme updates disabled."
            )
    except Exception:
        LOGGER.debug("Failed to enable live theme updates", exc_info=True)


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

    theme = _get_theme()

    if theme == "Unknown":
        theme = "Light"

    try:
        _apply_light(window) if theme == "Light" else _apply_dark(window)
    except Exception:
        LOGGER.error("Theme application failed", exc_info=True)


# =============================================================================
# PLATFORM HELPERS
# =============================================================================


def _is_windows() -> bool:
    """Return True if running on Windows OS.

    Returns:
        bool: True if on Windows, False otherwise.

    """
    return sys.platform == "win32" and hasattr(sys, "getwindowsversion")


def _is_windows_11_or_newer() -> bool:
    """Return True if running on Windows 11 or newer.

    Returns:
        bool: True if on Windows 11 or newer, False otherwise.

    """
    if not _is_windows():
        return False
    try:
        ver = sys.getwindowsversion()
        return int(ver.major) >= 10 and int(ver.build) >= 22000
    except Exception:
        return False


# =============================================================================
# THEME DETECTION
# =============================================================================


def _get_theme_windows() -> str:
    """Detect theme from the Windows registry.

    Returns:
        str: ``'Dark'``, ``'Light'``.

    """
    try:
        ver = sys.getwindowsversion()
        if ver.major < 10:
            return "Light"

        import winreg

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion"
            r"\Themes\Personalize",
        ) as key:
            value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")

        return "Dark" if value == 0 else "Light"
    except Exception:
        return "Light"


def _get_theme_qt_hints() -> str:
    """Detect theme via Qt 6.5+ QStyleHints.colorScheme().

    Returns:
        str: ``'Dark'``, ``'Light'``, or ``'Unknown'`` if unsupported.

    """
    try:
        hints = QtGui.QGuiApplication.styleHints()
        if not hasattr(hints, "colorScheme"):
            return "Unknown"
        scheme = hints.colorScheme()
        color_scheme = getattr(QtCore.Qt, "ColorScheme", None)
        if color_scheme is None:
            return "Unknown"
        if scheme == color_scheme.Dark:
            return "Dark"
        if scheme == color_scheme.Light:
            return "Light"
    except Exception:
        pass
    return "Unknown"


def _get_theme_palette() -> str:
    """Detect theme by measuring the application palette background luminance.

    Used as a last-resort fallback when Qt style hints are unavailable.
    Reads the Window background colour from the active QPalette; low
    lightness indicates a dark theme.

    Returns:
        str: ``'Dark'``, ``'Light'``, or ``'Unknown'``.

    """
    try:
        app = QtWidgets.QApplication.instance()
        if app is not None:
            bg = app.palette().color(QtGui.QPalette.ColorRole.Window)
            if bg.isValid():
                return "Dark" if bg.lightness() < 128 else "Light"
    except Exception:
        pass
    return "Unknown"


def _get_theme() -> str:
    """Detect the current system theme (light or dark).

    Delegates to platform-specific and layered detection helpers.
    Returns ``'Dark'``, ``'Light'``, or ``'Unknown'``.

    Detection order:

    1. Windows registry (on Windows).
    2. Qt 6.5+ ``QStyleHints.colorScheme()``.
    3. System palette luminance.

    Returns:
        str: ``'Dark'``, ``'Light'``, or ``'Unknown'``.

    """
    if _is_windows():
        return _get_theme_windows()

    result = _get_theme_qt_hints()
    if result != "Unknown":
        return result

    return _get_theme_palette()


# =============================================================================
# THEME APPLICATION
# =============================================================================


def _apply_light(window) -> None:
    """Apply light theme to the window."""
    if not _is_windows():
        return

    try:
        window.setStyleSheet("""
            QWidget#MainDialog {
                color: #000000;
                background-color: #ffffff;
            }
            """)
    except Exception as error:
        LOGGER.error("Failed to apply light theme: %s", error)


def _apply_dark(window) -> None:
    """Apply dark theme to the window."""
    if not _is_windows():
        return

    try:
        try:
            from ctypes import byref, c_int, c_void_p, sizeof, windll

            hwnd = int(window.winId())
            for attr in (20, 19):
                windll.dwmapi.DwmSetWindowAttribute(
                    c_void_p(hwnd),
                    c_int(attr),
                    byref(c_int(1)),
                    sizeof(c_int),
                )
        except Exception as dwm_error:
            LOGGER.debug("DWM dark titlebar failed: %s", dwm_error)

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
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                )
            )

            base_path = os.path.join(project_root, "assets")

        full_path = os.path.join(base_path, filename)
        return full_path

    except Exception:
        LOGGER.error(
            "Failed to resolve resource path for '%s'",
            filename,
            exc_info=True,
        )
        return filename  # fallback, may fail gracefully


# =============================================================================
# IMAGE UTILITIES
# =============================================================================


def backdrop(element) -> None:
    """Set a backdrop image to a widget.

    Load 'images/Backdrop.png' from resources and scale it to fill
    the element.

    Args:
        element (QtWidgets.QLabel): The widget to apply the backdrop to.

    """
    try:
        image_path = resource_path("images/Backdrop.png")

        if not os.path.exists(image_path):
            LOGGER.warning("Backdrop image not found: %s", image_path)
            return

        element.setPixmap(QtGui.QPixmap(image_path))
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

        window.setWindowIcon(QtGui.QIcon(icon_path))
        LOGGER.debug("Window icon set successfully: %s", icon_path)

    except Exception as error:
        LOGGER.error("Failed to set window icon: %s", error)
