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

# Windows version and DWM constants.  Windows keeps the major version at 10
# for Windows 11 and later, so feature gates must use the build number.
_WINDOWS_11_BUILD = 22000
_WINDOWS_MICA_BUILD = 22621
_DWMWA_USE_IMMERSIVE_DARK_MODE = (20, 19)
_DWMWA_SYSTEMBACKDROP_TYPE = 38
_DWMSBT_MAINWINDOW = 2

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
                lambda *_: QtCore.QTimer.singleShot(
                    0, lambda: apply(window)
                )
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
    """Return whether the Windows build is Windows 11 or later."""
    return (_windows_build() or 0) >= _WINDOWS_11_BUILD


def _windows_build() -> Optional[int]:
    """Return the Windows build number, or ``None`` when unavailable.

    Build-number gates protect old Windows 10 and initial Windows 11 builds
    from DWM attributes they do not implement.
    """
    if not _is_windows():
        return None
    try:
        return int(sys.getwindowsversion().build)
    except (AttributeError, TypeError, ValueError):
        return None


def _supports_native_windows_theming() -> bool:
    """Return whether this Qt runtime can follow the Windows colour scheme.

    ``QStyleHints.setColorScheme`` was added in Qt 6.8.  Checking the
    member, rather than a version string, keeps this safe for PyQt6 wheels
    built against an older Qt release and leaves PyQt5 on the stylesheet
    fallback.
    """
    # Qt's Windows platform palette can lag or disagree with the user's
    # AppsUseLightTheme setting on Windows 10. Retain the proven registry +
    # stylesheet path there; native palette following is a Windows 11 feature.
    if not _is_windows_11_or_newer() or QT_API != "PyQt6":
        return False

    try:
        hints = QtGui.QGuiApplication.styleHints()
        return bool(
            hints
            and hasattr(hints, "setColorScheme")
            and hasattr(QtCore.Qt, "ColorScheme")
        )
    except Exception:
        return False


def _supports_windows_mica() -> bool:
    """Return whether DWM's documented system-backdrop API is available."""
    return (_windows_build() or 0) >= _WINDOWS_MICA_BUILD


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


def _set_dwm_int_attribute(window, attribute: int, value: int) -> None:
    """Set an integer DWM attribute, ignoring unsupported OS attributes."""
    try:
        from ctypes import byref, c_int, c_void_p, sizeof, windll

        dwm_value = c_int(value)
        result = windll.dwmapi.DwmSetWindowAttribute(
            c_void_p(int(window.winId())),
            c_int(attribute),
            byref(dwm_value),
            sizeof(dwm_value),
        )
        if result not in (0, None):
            LOGGER.debug(
                "DWM rejected attribute %d (HRESULT %#x)",
                attribute,
                int(result),
            )
    except Exception as error:
        LOGGER.debug("DWM attribute %d unavailable: %s", attribute, error)


def _set_windows_chrome(window, dark: bool) -> None:
    """Apply title-bar colour and Mica only when their OS APIs exist."""
    # Attribute 20 is current; attribute 19 covers early Windows 10 builds.
    # Unsupported attributes return an HRESULT, so attempting both is safe.
    for attribute in _DWMWA_USE_IMMERSIVE_DARK_MODE:
        _set_dwm_int_attribute(window, attribute, int(dark))

    if _supports_windows_mica():
        _set_dwm_int_attribute(
            window, _DWMWA_SYSTEMBACKDROP_TYPE, _DWMSBT_MAINWINDOW
        )


def _apply_native_windows_theme(window, theme: str) -> None:
    """Let Qt 6.8+ follow Windows instead of imposing application colours."""
    hints = QtGui.QGuiApplication.styleHints()
    # Unknown removes any explicit application override and follows Windows.
    hints.setColorScheme(QtCore.Qt.ColorScheme.Unknown)
    # This module owns the legacy stylesheet, so remove it before Qt applies
    # its native palette.  This is also needed after a runtime binding/theme
    # transition in a long-lived process.
    window.setStyleSheet("")
    _set_windows_chrome(window, theme == "Dark")


def _legacy_windows_style(theme: str) -> str:
    """Return Atlas's compatible Windows 10/PyQt5 stylesheet."""
    if theme == "Light":
        return _WINDOWS_LIGHT_STYLE

    style = _WINDOWS_DARK_STYLE + _WINDOWS_DARK_BUTTON_STYLE
    if _is_windows_11_or_newer():
        return style + "QPushButton { border-radius: 4px; }"
    return style + _WINDOWS_10_PROGRESS_STYLE


def _apply_windows_theme(window, theme: str) -> None:
    """Apply native Windows 11 theme support or the legacy fallback."""
    dark = theme == "Dark"
    if _supports_native_windows_theming():
        _apply_native_windows_theme(window, theme)
        return

    _set_windows_chrome(window, dark)
    window.setStyleSheet(_legacy_windows_style(theme))


def _apply_light(window) -> None:
    """Apply light theme to the window."""
    if not _is_windows():
        return

    try:
        _apply_windows_theme(window, "Light")
    except Exception as error:
        LOGGER.error("Failed to apply light theme: %s", error)


def _apply_dark(window) -> None:
    """Apply dark theme to the window."""
    if not _is_windows():
        return

    try:
        _apply_windows_theme(window, "Dark")
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


def _is_tiling_wm() -> bool:
    """Return whether the desktop is a tiling WM.

    This compatibility alias keeps existing UI imports stable while sharing
    the session detection that selects the Linux Qt platform backend.
    """
    return _is_tiling_window_manager()


def backdrop(element) -> None:
    """Set a backdrop image to a widget.

    Load 'images/Backdrop.png' from resources and scale it to fill
    the element. Automatically disabled on tiling WMs.

    Args:
        element (QtWidgets.QLabel): The widget to apply the backdrop to.

    """
    if _is_tiling_wm():
        LOGGER.info("Tiling WM detected. Backdrop disabled.")
        return
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

    Use the SVG asset on Linux and the ICO asset on Windows.

    Args:
        window (QWidget): The window to set the icon for.

    """
    try:
        icon_filename = "icons/Icon.ico" if _is_windows() else "icons/Icon.svg"
        icon_path = resource_path(icon_filename)

        if not os.path.exists(icon_path):
            LOGGER.warning("Icon file not found: %s", icon_path)
            return

        window.setWindowIcon(QtGui.QIcon(icon_path))
        LOGGER.debug("Window icon set successfully: %s", icon_path)

    except Exception as error:
        LOGGER.error("Failed to set window icon: %s", error)
