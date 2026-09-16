"""Atlas | Packages | Themes.

Theme detection and application for Atlas.

On modern PyQt6/Qt builds on Windows, Qt follows the system colour
scheme through ``QStyleHints`` and supplies the platform palette. Older
Qt builds, including PyQt5, retain the stylesheet fallback. Windows 11
also receives a system-drawn Mica title-bar backdrop where supported.
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
from enum import IntEnum
from types import MappingProxyType
from typing import Optional

from atlas.compatibility.qt import (
    QT_API,
    QtCore,
    QtGui,
    QtWidgets,
    _is_tiling_window_manager,
)

# =============================================================================
# LOGGING
# =============================================================================

LOGGER = logging.getLogger(__name__)

# =============================================================================
# CONSTANTS
# =============================================================================

_WINDOWS_BUILD_FEATURES = MappingProxyType({
    "dark_titlebar": 17763,
    "win11_style": 22000,
    "mica_backdrop": 22621,
})

_DWMWA_USE_IMMERSIVE_DARK_MODE = (20, 19)
_DWMWA_SYSTEMBACKDROP_TYPE = 38
_DWMWA_WINDOW_CORNER_PREFERENCE = 33

class SystemBackdropType(IntEnum):
    """System backdrop types for Windows 11 22H2+."""
    AUTO = 0
    DISABLE = 1
    MAINWINDOW = 2       # Mica (Standard)
    TRANSIENTWINDOW = 3  # Acrylic
    TABBEDWINDOW = 4     # Mica Alt

class WindowCornerPreference(IntEnum):
    """Window corner preferences for Windows 11 21H2+."""
    DEFAULT = 0
    DONOTROUND = 1
    ROUND = 2
    ROUNDSMALL = 3

_WINDOWS_LIGHT_STYLE = """
    QWidget#MainDialog {
        color: #000000;
        background-color: #ffffff;
    }
"""

_WINDOWS_DARK_STYLE = """
    QWidget#MainDialog, QMessageBox {
        background-color: #1e1e1e;
    }
    QLabel {
        color: white;
    }
"""

_WINDOWS_DARK_BUTTON_STYLE = """
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

_WINDOWS_10_PROGRESS_STYLE = """
    QProgressBar {
        border: 1px solid #555;
        background-color: #2b2b2b;
        text-align: center;
        color: white;
        height: 12px;
    }
"""

# =============================================================================
# THEME DETECTION
# =============================================================================

class ThemeDetector:
    """Handles detection of the current system theme across platforms."""

    @classmethod
    def detect(cls) -> str:
        """Detect the current system theme.
        
        Returns:
            str: 'Dark', 'Light', or 'Unknown'.
        """
        if cls._is_windows():
            return cls._query_windows_registry()

        result = cls._query_qt_hints()
        if result != "Unknown":
            return result

        return cls._query_palette()

    @staticmethod
    def _is_windows() -> bool:
        """Return True if running on Windows OS."""
        return sys.platform == "win32" and hasattr(sys, "getwindowsversion")

    @classmethod
    def _query_windows_registry(cls) -> str:
        """Detect theme from the Windows registry."""
        try:
            ver = sys.getwindowsversion()
            if ver.major < 10:
                return "Light"

            import winreg

            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
            ) as key:
                value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")

            return "Dark" if value == 0 else "Light"
        except Exception:
            return "Light"

    @staticmethod
    def _query_qt_hints() -> str:
        """Detect theme via Qt 6.5+ QStyleHints.colorScheme()."""
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

    @staticmethod
    def _query_palette() -> str:
        """Detect theme by measuring the application palette background luminance."""
        try:
            app = QtWidgets.QApplication.instance()
            if app is not None:
                bg = app.palette().color(QtGui.QPalette.ColorRole.Window)
                if bg.isValid():
                    return "Dark" if bg.lightness() < 128 else "Light"
        except Exception:
            pass
        return "Unknown"

# =============================================================================
# WINDOWS CHROME MANAGEMENT
# =============================================================================

class WindowsChromeManager:
    """Manages Windows DWM API interactions for native window chrome."""

    @classmethod
    def supports(cls, feature: str) -> bool:
        """Return whether the current Windows build supports a named feature."""
        min_build = _WINDOWS_BUILD_FEATURES.get(feature)
        if min_build is None:
            return False
        return (cls._windows_build() or 0) >= min_build

    @staticmethod
    def _windows_build() -> Optional[int]:
        """Return the Windows build number, or None when unavailable."""
        if not ThemeDetector._is_windows():
            return None
        try:
            return int(sys.getwindowsversion().build)
        except (AttributeError, TypeError, ValueError):
            return None

    @staticmethod
    def _set_dwm_int(window, attribute: int, value: int) -> None:
        """Set an integer DWM attribute via ctypes."""
        try:
            import ctypes
            
            dwmapi = ctypes.windll.dwmapi
            
            # Define argtypes and restype explicitly for robust native boundaries
            dwmapi.DwmSetWindowAttribute.argtypes = [
                ctypes.c_void_p,  # hwnd
                ctypes.c_int,     # dwAttribute
                ctypes.c_void_p,  # pvAttribute
                ctypes.c_int,     # cbAttribute
            ]
            dwmapi.DwmSetWindowAttribute.restype = ctypes.c_long

            dwm_value = ctypes.c_int(value)
            result = dwmapi.DwmSetWindowAttribute(
                int(window.winId()),
                attribute,
                ctypes.byref(dwm_value),
                ctypes.sizeof(dwm_value),
            )
            if result not in (0, None):
                LOGGER.debug("DWM rejected attr %d (HRESULT %#x)", attribute, int(result))
        except Exception as error:
            LOGGER.debug("DWM attribute %d unavailable: %s", attribute, error)

    @classmethod
    def apply_chrome(cls, window, dark: bool) -> None:
        """Apply title-bar colour, window corners, and system backdrop effects."""
        for attr in _DWMWA_USE_IMMERSIVE_DARK_MODE:
            cls._set_dwm_int(window, attr, int(dark))

        if cls.supports("win11_style"):
            cls._set_dwm_int(window, _DWMWA_WINDOW_CORNER_PREFERENCE, WindowCornerPreference.ROUND)

        if cls.supports("mica_backdrop"):
            cls._set_dwm_int(window, _DWMWA_SYSTEMBACKDROP_TYPE, SystemBackdropType.MAINWINDOW)

# =============================================================================
# PLATFORM THEMERS
# =============================================================================

class WindowsThemer:
    """Handles applying the appropriate theme specifically for Windows."""

    @classmethod
    def apply(cls, window, theme: str) -> None:
        """Apply native Windows 11 theme support or the legacy fallback."""
        try:
            dark = (theme == "Dark")
            if cls._supports_native():
                cls._apply_native(window, dark)
            else:
                WindowsChromeManager.apply_chrome(window, dark)
                window.setStyleSheet(cls._legacy_style(theme))
        except Exception:
            LOGGER.error("Failed to apply Windows theme", exc_info=True)

    @classmethod
    def _supports_native(cls) -> bool:
        """Return whether this Qt runtime can follow the Windows colour scheme."""
        if not WindowsChromeManager.supports("win11_style") or QT_API != "PyQt6":
            return False
        try:
            hints = QtGui.QGuiApplication.styleHints()
            return bool(hints and hasattr(hints, "setColorScheme") and hasattr(QtCore.Qt, "ColorScheme"))
        except Exception:
            return False

    @classmethod
    def _apply_native(cls, window, dark: bool) -> None:
        """Let Qt 6.8+ follow Windows natively."""
        app = QtWidgets.QApplication.instance()
        if app and hasattr(app, "setStyle"):
            try:
                if "windows11" in [s.lower() for s in QtWidgets.QStyleFactory.keys()]:
                    app.setStyle("windows11")
            except Exception as error:
                LOGGER.debug("Could not apply windows11 style: %s", error)

        hints = QtGui.QGuiApplication.styleHints()
        if hints and hasattr(hints, "setColorScheme"):
            hints.setColorScheme(QtCore.Qt.ColorScheme.Unknown)

        window.setStyleSheet("")
        WindowsChromeManager.apply_chrome(window, dark)

    @staticmethod
    def _legacy_style(theme: str) -> str:
        """Return the legacy Windows 10/PyQt5 stylesheet."""
        if theme == "Light":
            return _WINDOWS_LIGHT_STYLE
        style = _WINDOWS_DARK_STYLE + _WINDOWS_DARK_BUTTON_STYLE
        if WindowsChromeManager.supports("win11_style"):
            return style + "QPushButton { border-radius: 4px; }"
        return style + _WINDOWS_10_PROGRESS_STYLE

# =============================================================================
# RESOURCE AND IMAGE UTILITIES
# =============================================================================

class ImageManager:
    """Manages icon loading, UI images, and resource path resolution."""

    @staticmethod
    def resource_path(filename: str) -> Optional[str]:
        """Return the absolute path to a resource file safely.
        
        Args:
            filename (str): Name of the resource file.
            
        Returns:
            Optional[str]: Absolute path to the resource, or None if validation fails.
        """
        try:
            if getattr(sys, "frozen", False):
                base_path = os.path.abspath(os.path.join(getattr(sys, "_MEIPASS", os.getcwd()), "assets"))
            else:
                project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
                base_path = os.path.abspath(os.path.join(project_root, "assets"))
            
            full_path = os.path.abspath(os.path.join(base_path, filename))
            
            # Prevent directory traversal escaping the assets directory
            if not full_path.startswith(base_path):
                LOGGER.error("Resource path traversal attempt detected: %s", filename)
                return None
                
            return full_path
        except Exception:
            LOGGER.error("Failed to resolve resource path for '%s'", filename, exc_info=True)
            return None

    @classmethod
    def apply_backdrop(cls, element) -> None:
        """Set a backdrop image to a widget."""
        if _is_tiling_window_manager():
            LOGGER.info("Tiling WM detected. Backdrop disabled.")
            return
        try:
            image_path = cls.resource_path("images/Backdrop.png")
            if image_path is None or not os.path.exists(image_path):
                LOGGER.warning("Backdrop image not found or invalid: %s", image_path)
                return

            pixmap = QtGui.QPixmap(image_path)
            if pixmap.isNull():
                LOGGER.warning("Backdrop image could not be loaded: %s", image_path)
                return

            element.setPixmap(pixmap)
            element.setScaledContents(True)
        except Exception as error:
            LOGGER.error("Failed to set backdrop: %s", error)

    @classmethod
    def apply_icon(cls, window) -> None:
        """Set the application window icon."""
        try:
            icon_filename = "icons/Icon.ico" if ThemeDetector._is_windows() else "icons/Icon.svg"
            icon_path = cls.resource_path(icon_filename)

            if icon_path is None or not os.path.exists(icon_path):
                LOGGER.warning("Icon file not found or invalid: %s", icon_path)
                return

            loaded_icon = QtGui.QIcon(icon_path)
            if loaded_icon.isNull():
                LOGGER.warning("Icon could not be loaded: %s", icon_path)
                return

            window.setWindowIcon(loaded_icon)
        except Exception as error:
            LOGGER.error("Failed to set window icon: %s", error)

# =============================================================================
# PUBLIC FACADE (Backwards Compatibility)
# =============================================================================

def initialize(window) -> None:
    """Initialize the theming system for the application window."""
    if not window:
        LOGGER.warning("No window provided for theme initialization.")
        return

    icon(window)
    backdrop_label = window.findChild(QtWidgets.QLabel, "Backdrop")
    if backdrop_label:
        backdrop(backdrop_label)
    
    apply(window)

    try:
        hints = QtGui.QGuiApplication.styleHints()
        if hints and hasattr(hints, "colorSchemeChanged"):
            hints.colorSchemeChanged.connect(
                lambda *_: QtCore.QTimer.singleShot(0, lambda: apply(window))
            )
        else:
            LOGGER.debug("colorSchemeChanged unavailable; live theme updates disabled.")
    except Exception:
        LOGGER.debug("Failed to enable live theme updates", exc_info=True)


def apply(window) -> None:
    """Apply the detected system theme to the provided window."""
    if not window:
        LOGGER.warning("No window provided! Skipping theme application.")
        return

    theme = ThemeDetector.detect()
    if theme == "Unknown":
        theme = "Light"

    if ThemeDetector._is_windows():
        WindowsThemer.apply(window, theme)


def icon(window) -> None:
    """Set the application window icon."""
    ImageManager.apply_icon(window)


def backdrop(element) -> None:
    """Set a backdrop image to a widget."""
    ImageManager.apply_backdrop(element)


def _is_tiling_wm() -> bool:
    """Compatibility alias for UI elements."""
    return _is_tiling_window_manager()
