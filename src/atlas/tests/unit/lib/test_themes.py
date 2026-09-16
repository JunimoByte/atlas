"""Atlas | Tests | Packages | Themes.

Unit tests for the themes module.
"""

# =============================================================================
# IMPORTS
# =============================================================================

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

from atlas.lib import themes

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def mock_window() -> MagicMock:
    """Provide a mocked window object."""
    window = MagicMock()
    window.winId.return_value = 12345
    return window


# =============================================================================
# TESTS
# =============================================================================


def test_apply_with_none_window(caplog: pytest.LogCaptureFixture) -> None:
    """Verify that a warning is logged if no window is provided."""
    caplog.set_level("WARNING", logger="atlas.lib.themes")
    themes.apply(None)
    assert any("No window provided" in rec.message for rec in caplog.records)


def test_initialize_accepts_color_scheme_signal_value(
    monkeypatch: pytest.MonkeyPatch, mock_window: MagicMock
) -> None:
    """Qt's color-scheme signal can pass its new scheme to the callback."""
    connected = []
    signal = MagicMock()
    signal.connect.side_effect = connected.append
    hints = MagicMock(colorSchemeChanged=signal)
    apply_theme = MagicMock()

    monkeypatch.setattr(themes, "icon", MagicMock())
    monkeypatch.setattr(themes, "apply", apply_theme)
    monkeypatch.setattr(
        themes.QtGui.QGuiApplication, "styleHints", lambda: hints
    )
    monkeypatch.setattr(
        themes.QtCore.QTimer,
        "singleShot",
        lambda _delay, callback: callback(),
    )
    mock_window.findChild.return_value = None

    themes.initialize(mock_window)
    connected[0](themes.QtCore.Qt.ColorScheme.Dark)

    assert apply_theme.call_count == 2


@pytest.mark.parametrize(
    "theme_name",
    ["Light", "Dark"],
)
def test_apply_calls_windows_themer(
    mock_window: MagicMock,
    theme_name: str,
) -> None:
    """Verify that apply delegates to WindowsThemer on Windows."""
    with patch("atlas.lib.themes.ThemeDetector.detect", return_value=theme_name):
        with patch("atlas.lib.themes.ThemeDetector._is_windows", return_value=True):
            with patch("atlas.lib.themes.WindowsThemer.apply") as mock_target:
                themes.apply(mock_window)
                mock_target.assert_called_once_with(mock_window, theme_name)


def test_get_theme_windows_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify the fallback to Light theme if registry access fails."""
    monkeypatch.setattr(themes.ThemeDetector, "_is_windows", lambda: True)
    monkeypatch.setattr(
        sys,
        "getwindowsversion",
        lambda: type("WinVer", (), {"major": 10})(),
        raising=False,
    )

    class FakeWinreg:
        def open_key(self, *args, **kwargs):
            raise Exception("fail")
        OpenKey = open_key

    sys.modules["winreg"] = FakeWinreg()

    try:
        assert themes.ThemeDetector._query_windows_registry() == "Light"
    finally:
        del sys.modules["winreg"]


def test_get_theme_linux(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify theme detection on Linux fallback."""
    monkeypatch.setattr(themes.ThemeDetector, "_is_windows", lambda: False)
    assert themes.ThemeDetector.detect() in ("Light", "Dark", "Unknown")


def test_apply_light_sets_stylesheet(
    monkeypatch: pytest.MonkeyPatch, mock_window: MagicMock
) -> None:
    """Verify that the Light theme stylesheet is applied on Windows."""
    monkeypatch.setattr(themes.ThemeDetector, "_is_windows", lambda: True)
    monkeypatch.setattr(
        sys,
        "getwindowsversion",
        lambda: type("WinVer", (), {"major": 10})(),
        raising=False,
    )
    monkeypatch.setattr(
        themes.WindowsThemer, "_supports_native", lambda: False
    )
    themes.WindowsThemer.apply(mock_window, "Light")

    mock_window.setStyleSheet.assert_called_once()
    style = mock_window.setStyleSheet.call_args[0][0]
    assert "background-color: #ffffff" in style


def test_apply_linux_skips_windows_themer(
    monkeypatch: pytest.MonkeyPatch, mock_window: MagicMock
) -> None:
    """Verify theme application on Linux skips calling Windows-specific styling."""
    monkeypatch.setattr(themes.ThemeDetector, "_is_windows", lambda: False)
    with patch("atlas.lib.themes.WindowsThemer.apply") as mock_windows_apply:
        themes.apply(mock_window)
        mock_windows_apply.assert_not_called()
        mock_window.setStyleSheet.assert_not_called()


def test_apply_dark_calls_dwmapi(
    monkeypatch: pytest.MonkeyPatch, mock_window: MagicMock
) -> None:
    """Verify that Dark theme attributes are applied on Windows."""
    monkeypatch.setattr(themes.ThemeDetector, "_is_windows", lambda: True)
    monkeypatch.setattr(
        sys,
        "getwindowsversion",
        lambda: type("WinVer", (), {"major": 10})(),
        raising=False,
    )

    mock_dwm = MagicMock()
    monkeypatch.setattr(
        themes.WindowsThemer, "_supports_native", lambda: False
    )

    with patch("ctypes.windll", create=True) as mock_windll:
        mock_windll.dwmapi = mock_dwm
        themes.WindowsThemer.apply(mock_window, "Dark")

        assert mock_dwm.DwmSetWindowAttribute.call_count == 2
        mock_window.setStyleSheet.assert_called_once()


def test_apply_native_windows_theme_uses_qt_palette(
    monkeypatch: pytest.MonkeyPatch, mock_window: MagicMock
) -> None:
    """Modern PyQt6 uses Qt's system-following colour scheme API."""
    hints = MagicMock()
    monkeypatch.setattr(
        themes.QtGui.QGuiApplication, "styleHints", lambda: hints
    )
    monkeypatch.setattr(themes.WindowsChromeManager, "apply_chrome", MagicMock())

    themes.WindowsThemer._apply_native(mock_window, True)

    hints.setColorScheme.assert_called_once_with(
        themes.QtCore.Qt.ColorScheme.Unknown
    )
    mock_window.setStyleSheet.assert_called_once_with("")
    themes.WindowsChromeManager.apply_chrome.assert_called_once_with(mock_window, True)


def test_native_windows_theming_requires_pyqt6(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """PyQt5 always uses the compatible stylesheet fallback."""
    monkeypatch.setattr(themes.ThemeDetector, "_is_windows", lambda: True)
    monkeypatch.setattr(themes, "QT_API", "PyQt5")

    assert not themes.WindowsThemer._supports_native()


def test_native_windows_theming_requires_windows_11(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Windows 10 retains the reliable registry and stylesheet fallback."""
    monkeypatch.setattr(themes.WindowsChromeManager, "supports", lambda _feature: False)
    monkeypatch.setattr(themes, "QT_API", "PyQt6")

    assert not themes.WindowsThemer._supports_native()


def test_windows_build_handles_legacy_or_incomplete_version_info(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Incomplete version data leaves advanced Windows features disabled."""
    monkeypatch.setattr(themes.ThemeDetector, "_is_windows", lambda: True)
    monkeypatch.setattr(
        sys,
        "getwindowsversion",
        lambda: type("WinVer", (), {})(),
        raising=False,
    )

    assert themes.WindowsChromeManager._windows_build() is None
    assert not themes.WindowsChromeManager.supports("win11_style")
    assert not themes.WindowsChromeManager.supports("mica_backdrop")


def test_legacy_windows_style_keeps_windows_10_progress_bar(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The fallback styling remains intact for Windows 10 and PyQt5."""
    monkeypatch.setattr(themes.WindowsChromeManager, "supports", lambda _feature: False)

    style = themes.WindowsThemer._legacy_style("Dark")

    assert "QProgressBar" in style
    assert "border-radius" not in style


def test_windows_11_chrome_enables_mica(
    monkeypatch: pytest.MonkeyPatch, mock_window: MagicMock
) -> None:
    """Windows 11 22H2+ enables the system Mica backdrop."""
    monkeypatch.setattr(themes.WindowsChromeManager, "supports", lambda _feature: True)
    mock_dwm = MagicMock()

    with patch("ctypes.windll", create=True) as mock_windll:
        mock_windll.dwmapi = mock_dwm
        themes.WindowsChromeManager.apply_chrome(mock_window, True)

    assert mock_dwm.DwmSetWindowAttribute.call_count == 4
    # Check that DWMWA_SYSTEMBACKDROP_TYPE (38) was passed with MAINWINDOW (2)
    assert mock_dwm.DwmSetWindowAttribute.call_args_list[-1].args[1] == 38


def test_resource_path_dev(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify the resource path in development mode."""
    monkeypatch.setattr(sys, "frozen", False, raising=False)

    path = themes.ImageManager.resource_path("file.txt")

    assert "assets" in path
    assert path.endswith("file.txt")


def test_resource_path_traversal_prevention(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify that resource_path prevents escaping the assets directory."""
    monkeypatch.setattr(sys, "frozen", False, raising=False)
    
    path = themes.ImageManager.resource_path("../file.txt")
    
    assert path is None


def test_resource_path_frozen(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify the resource path in frozen mode."""
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    fake_meipass = os.path.abspath(os.path.join("fake", "meipass"))
    monkeypatch.setattr(sys, "_MEIPASS", fake_meipass, raising=False)

    path = themes.ImageManager.resource_path("file.txt")

    assert path.startswith(fake_meipass)
    assert path.endswith("file.txt")


def test_backdrop_sets_pixmap(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify that a backdrop pixmap is set."""
    mock_element = MagicMock()

    monkeypatch.setattr(themes.ImageManager, "resource_path", lambda x: "exists.png")
    monkeypatch.setattr(os.path, "exists", lambda x: True)

    class FakeQPixmap:
        def __init__(self, path):
            self.path = path
        def isNull(self):
            return False

    monkeypatch.setattr(themes.QtGui, "QPixmap", FakeQPixmap)

    themes.backdrop(mock_element)

    mock_element.setPixmap.assert_called_once()
    mock_element.setScaledContents.assert_called_once()


def test_icon_uses_svg_on_linux(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify that Linux uses the SVG window icon."""
    mock_window = MagicMock()
    requested_paths = []

    monkeypatch.setattr(themes.ThemeDetector, "_is_windows", lambda: False)
    monkeypatch.setattr(
        themes.ImageManager,
        "resource_path",
        lambda path: requested_paths.append(path) or "icon.svg",
    )
    monkeypatch.setattr(os.path, "exists", lambda x: True)

    class FakeQIcon:
        def __init__(self, path):
            self.path = path
        def isNull(self):
            return False

    monkeypatch.setattr(themes.QtGui, "QIcon", FakeQIcon)

    themes.icon(mock_window)

    assert requested_paths == ["icons/Icon.svg"]
    mock_window.setWindowIcon.assert_called_once()


def test_icon_uses_ico_on_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify that Windows retains the ICO window icon."""
    mock_window = MagicMock()
    requested_paths = []

    monkeypatch.setattr(themes.ThemeDetector, "_is_windows", lambda: True)
    monkeypatch.setattr(
        themes.ImageManager,
        "resource_path",
        lambda path: requested_paths.append(path) or "icon.ico",
    )
    monkeypatch.setattr(os.path, "exists", lambda x: True)

    class FakeQIcon:
        def __init__(self, path):
            self.path = path
        def isNull(self):
            return False

    monkeypatch.setattr(themes.QtGui, "QIcon", FakeQIcon)

    themes.icon(mock_window)

    assert requested_paths == ["icons/Icon.ico"]
    mock_window.setWindowIcon.assert_called_once()

# =============================================================================
# TEST EXECUTION
# =============================================================================

if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
