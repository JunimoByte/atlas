"""Atlas | Tests | Packages | Permissions.

Unit tests for cross-platform permission validation in Atlas.
"""

# =============================================================================
# IMPORTS
# =============================================================================

import platform
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from atlas.lib import permissions

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def mock_unix_root(monkeypatch: pytest.MonkeyPatch) -> None:
    """Simulate root user on Unix-like systems."""
    monkeypatch.setattr(permissions, "os", type("os_mock", (), {})())
    setattr(permissions.os, "geteuid", lambda: 0)
    monkeypatch.setattr(platform, "system", lambda: "Linux")


@pytest.fixture
def mock_unix_nonroot(monkeypatch: pytest.MonkeyPatch) -> None:
    """Simulate non-root user on Unix-like systems."""
    monkeypatch.setattr(permissions, "os", type("os_mock", (), {})())
    setattr(permissions.os, "geteuid", lambda: 1000)
    monkeypatch.setattr(platform, "system", lambda: "Linux")


@pytest.fixture
def mock_windows_admin(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Simulate Windows admin user."""
    monkeypatch.setattr(platform, "system", lambda: "Windows")
    monkeypatch.delattr(permissions.os, "geteuid", raising=False)
    mock_admin = MagicMock(return_value=1)
    mock_windll = MagicMock()
    mock_windll.shell32.IsUserAnAdmin = mock_admin
    monkeypatch.setattr(
        permissions.ctypes, "windll", mock_windll, raising=False
    )
    return mock_admin


@pytest.fixture
def mock_windows_nonadmin(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Simulate Windows non-admin user."""
    monkeypatch.setattr(platform, "system", lambda: "Windows")
    monkeypatch.delattr(permissions.os, "geteuid", raising=False)
    mock_admin = MagicMock(return_value=0)
    mock_windll = MagicMock()
    mock_windll.shell32.IsUserAnAdmin = mock_admin
    monkeypatch.setattr(
        permissions.ctypes, "windll", mock_windll, raising=False
    )
    return mock_admin


@pytest.fixture
def mock_exit(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Mock sys.exit to prevent the test runner from exiting."""
    mock = MagicMock()
    monkeypatch.setattr(sys, "exit", mock)
    return mock


# =============================================================================
# TESTS
# =============================================================================


def test_is_elevated_unix_root(mock_unix_root: None) -> None:
    """Verify detection of elevated privileges on Unix (root)."""
    assert permissions.is_elevated() is True


def test_is_elevated_unix_nonroot(mock_unix_nonroot: None) -> None:
    """Verify detection of non-elevated privileges on Unix (non-root)."""
    assert permissions.is_elevated() is False


def test_is_elevated_windows_admin(mock_windows_admin: MagicMock) -> None:
    """Verify detection of elevated privileges on Windows (admin)."""
    assert permissions.is_elevated() is True
    mock_windows_admin.assert_called_once()


def test_is_elevated_windows_nonadmin(
    mock_windows_nonadmin: MagicMock,
) -> None:
    """Verify detection of non-elevated privileges on Windows (non-admin)."""
    assert permissions.is_elevated() is False
    mock_windows_nonadmin.assert_called_once()


def test_is_elevated_fails_safely(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify that is_elevated fails safely upon error."""
    monkeypatch.setattr(permissions, "os", type("os_mock", (), {})())
    setattr(
        permissions.os,
        "geteuid",
        lambda: (_ for _ in ()).throw(Exception("fail")),
    )
    monkeypatch.setattr(platform, "system", lambda: "Linux")
    assert permissions.is_elevated() is False


def test_show_elevated_permissions_dialog_calls_popup(
    monkeypatch: pytest.MonkeyPatch, mock_exit: MagicMock
) -> None:
    """Verify that the permissions dialog shows a warning and exits."""
    mock_warning = MagicMock()
    monkeypatch.setattr("atlas.display.popup.show_warning", mock_warning)

    permissions.show_elevated_permissions_dialog()

    mock_warning.assert_called_once()
    mock_exit.assert_called_once_with(1)


def test_show_elevated_permissions_dialog_fallback(
    monkeypatch: pytest.MonkeyPatch, mock_exit: MagicMock
) -> None:
    """Verify the fallback to logging and exit if the dialog fails."""

    def raise_import_error(*args, **kwargs):
        """Raise ImportError always."""
        raise ImportError("fail")

    monkeypatch.setattr("atlas.display.popup.show_warning", raise_import_error)

    permissions.show_elevated_permissions_dialog()
    mock_exit.assert_called_once_with(1)


# =============================================================================
# TESTS — macOS TCC / Full Disk Access
# =============================================================================


def test_needs_fda_returns_false_on_non_darwin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """needs_full_disk_access returns False on non-macOS."""
    monkeypatch.setattr(platform, "system", lambda: "Windows")
    assert permissions.needs_full_disk_access() is False


def test_needs_fda_returns_false_when_dir_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    """needs_full_disk_access returns False when Safari dir absent."""
    monkeypatch.setattr(platform, "system", lambda: "Darwin")
    monkeypatch.setattr(
        permissions,
        "_TCC_TEST_PATH",
        str(tmp_path / "nonexistent"),
    )
    assert permissions.needs_full_disk_access() is False


def test_needs_fda_returns_false_when_readable(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    """needs_full_disk_access returns False when dir is readable."""
    safari = tmp_path / "Safari"
    safari.mkdir()
    monkeypatch.setattr(platform, "system", lambda: "Darwin")
    monkeypatch.setattr(
        permissions, "_TCC_TEST_PATH", str(safari)
    )
    assert permissions.needs_full_disk_access() is False


def test_needs_fda_returns_true_when_permission_denied(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    """needs_full_disk_access returns True on PermissionError."""
    from unittest.mock import patch

    safari = tmp_path / "Safari"
    safari.mkdir()
    monkeypatch.setattr(platform, "system", lambda: "Darwin")
    monkeypatch.setattr(
        permissions, "_TCC_TEST_PATH", str(safari)
    )
    with patch.object(
        permissions.os,
        "listdir",
        side_effect=PermissionError("TCC"),
    ):
        assert permissions.needs_full_disk_access() is True


def test_show_fda_dialog_returns_true_on_yes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """show_full_disk_access_dialog returns True when user clicks Yes."""
    captured = {}

    def mock_question(**kw):
        captured.update(kw)
        return True

    monkeypatch.setattr(
        "atlas.display.popup.show_question", mock_question
    )
    mock_open = MagicMock()
    monkeypatch.setattr(
        permissions, "_open_fda_preferences", mock_open
    )
    assert permissions.show_full_disk_access_dialog() is True
    mock_open.assert_called_once()
    assert captured.get("message") == "Full Disk Access Requested"
    assert "optional" in captured.get("details", "")


def test_show_fda_dialog_returns_false_on_no(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """show_full_disk_access_dialog returns False when user clicks No."""
    monkeypatch.setattr(
        "atlas.display.popup.show_question",
        lambda **kw: False,
    )
    assert permissions.show_full_disk_access_dialog() is False


# =============================================================================
# TEST EXECUTION
# =============================================================================

if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
