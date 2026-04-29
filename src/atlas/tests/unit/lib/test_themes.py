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


@pytest.mark.parametrize(
    "theme_name, target_mock, skipped_mock",
    [
        ("Light", "_apply_light", "_apply_dark"),
        ("Dark", "_apply_dark", "_apply_light"),
    ]
)
def test_apply_calls_correct_theme_function(
    mock_window: MagicMock, theme_name: str,
    target_mock: str, skipped_mock: str
) -> None:
    """Verify that the correct theme function is called."""
    with patch("atlas.lib.themes._get_theme", return_value=theme_name):
        with patch(f"atlas.lib.themes.{target_mock}") as mock_target:
            with patch(f"atlas.lib.themes.{skipped_mock}") as mock_skipped:
                themes.apply(mock_window)
                mock_target.assert_called_once_with(mock_window)
                mock_skipped.assert_not_called()


def test_get_theme_non_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify that Light theme is returned for non-Windows systems."""
    monkeypatch.setattr(themes, "OS", "linux")
    assert themes._get_theme() == "Light"


def test_get_theme_windows_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify the fallback to Light theme if registry access fails."""
    monkeypatch.setattr(themes, "OS", "windows")
    monkeypatch.setattr(
        sys, "getwindowsversion", lambda: type("WinVer", (), {"major": 10})()
    )

    class FakeWinreg:
        """Mock winreg module for Windows registry testing."""

        def OpenKey(self, *args, **kwargs):
            """Mock OpenKey to raise an exception."""
            raise Exception("fail")

    sys.modules["winreg"] = FakeWinreg()

    try:
        assert themes._get_theme() == "Light"
    finally:
        del sys.modules["winreg"]


def test_apply_light_sets_stylesheet(
    monkeypatch: pytest.MonkeyPatch, mock_window: MagicMock
) -> None:
    """Verify that the Light theme stylesheet is applied."""
    monkeypatch.setattr(themes, "OS", "windows")
    themes._apply_light(mock_window)

    mock_window.setStyleSheet.assert_called_once()
    style = mock_window.setStyleSheet.call_args[0][0]
    assert "background-color: #ffffff" in style


def test_apply_dark_calls_dwmapi(
    monkeypatch: pytest.MonkeyPatch, mock_window: MagicMock
) -> None:
    """Verify that Dark theme attributes are applied on Windows."""
    monkeypatch.setattr(themes, "OS", "windows")
    monkeypatch.setattr(
        sys, "getwindowsversion", lambda: type("WinVer", (), {"major": 10})()
    )

    mock_dwm = MagicMock()

    with patch("ctypes.windll") as mock_windll:
        mock_windll.dwmapi = mock_dwm
        themes._apply_dark(mock_window)

        assert mock_dwm.DwmSetWindowAttribute.call_count == 2
        mock_window.setStyleSheet.assert_called_once()


def test_resource_path_dev(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify the resource path in development mode."""
    monkeypatch.setattr(sys, "frozen", False, raising=False)

    path = themes.resource_path("file.txt")

    assert "assets" in path
    assert path.endswith("file.txt")


def test_resource_path_frozen(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify the resource path in frozen mode."""
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", "/fake/meipass", raising=False)

    path = themes.resource_path("file.txt")

    assert path.startswith("/fake/meipass")
    assert path.endswith("file.txt")


def test_backdrop_sets_pixmap(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify that a backdrop pixmap is set."""
    mock_element = MagicMock()

    monkeypatch.setattr(themes, "resource_path", lambda x: "exists.png")
    monkeypatch.setattr(os.path, "exists", lambda x: True)

    class FakeQPixmap:
        """Mock QPixmap for theme testing."""

        def __init__(self, path):
            """Initialise with a path."""
            self.path = path

    monkeypatch.setattr(themes, "QPixmap", FakeQPixmap)

    themes.backdrop(mock_element)

    mock_element.setPixmap.assert_called_once()
    mock_element.setScaledContents.assert_called_once()


def test_icon_sets_window_icon(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify that a window icon is set."""
    mock_window = MagicMock()

    monkeypatch.setattr(themes, "resource_path", lambda x: "icon.ico")
    monkeypatch.setattr(os.path, "exists", lambda x: True)

    class FakeQIcon:
        """Mock QIcon for theme testing."""

        def __init__(self, path):
            """Initialise with a path."""
            self.path = path

    monkeypatch.setattr(themes, "QIcon", FakeQIcon)

    themes.icon(mock_window)

    mock_window.setWindowIcon.assert_called_once()


# =============================================================================
# TEST EXECUTION
# =============================================================================


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
