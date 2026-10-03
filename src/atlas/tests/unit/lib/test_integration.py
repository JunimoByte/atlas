"""Atlas | Tests | Packages | Integration.

Unit tests for integration.py OS folder helpers.
"""

# =============================================================================
# IMPORTS
# =============================================================================

import subprocess
import sys
from pathlib import Path
from typing import List, Optional
from unittest.mock import MagicMock, patch

import pytest

from atlas.backup import archive as Archive  # noqa: N812
from atlas.lib import integration

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def temp_folder(tmp_path: Path) -> Path:
    """Create a temporary folder for testing."""
    folder = tmp_path / "test_folder"
    folder.mkdir()
    return folder


@pytest.fixture
def missing_folder(tmp_path: Path) -> Path:
    """Provide a folder path that does not exist."""
    return tmp_path / "missing_folder"


@pytest.fixture
def mock_warning(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Mock show_warning to verify warning messages."""
    mock = MagicMock()
    monkeypatch.setattr("atlas.lib.integration.show_warning", mock)
    return mock


# =============================================================================
# TESTS — open_folder
# =============================================================================


def test_open_folder_with_valid_path(temp_folder: Path) -> None:
    """Verify that valid folders are opened without errors."""
    with patch("atlas.lib.integration._open_folder_platform") as mock_open:
        integration.open_folder(temp_folder)
        mock_open.assert_called_once_with(temp_folder)


def test_open_folder_none_uses_zip_output_dir(
    tmp_path: Path,
) -> None:
    """Verify fallback to ZIP_OUTPUT_DIR from a prior run."""
    fake_dir = tmp_path / "archive_dir"
    fake_dir.mkdir()
    with patch.object(Archive, "ZIP_OUTPUT_DIR", fake_dir):
        with patch("atlas.lib.integration._open_folder_platform") as mock_open:
            integration.open_folder(None)
            mock_open.assert_called_once_with(fake_dir)


def test_open_folder_none_uses_default_output_dir(
    tmp_path: Path,
) -> None:
    """Verify fallback to _get_default_output_dir."""
    fake_dir = tmp_path / "default_dir"
    fake_dir.mkdir()
    with patch.object(Archive, "ZIP_OUTPUT_DIR", None):
        with patch.object(
            Archive, "_get_default_output_dir", return_value=fake_dir
        ):
            with patch(
                "atlas.lib.integration._open_folder_platform"
            ) as mock_open:
                integration.open_folder(None)
                mock_open.assert_called_once_with(fake_dir)


def test_open_folder_none_and_archive_none(
    mock_warning: MagicMock,
) -> None:
    """Verify warning is shown if no path resolves."""
    missing = Path("/tmp/_atlas_nonexistent_12345")
    with patch.object(Archive, "ZIP_OUTPUT_DIR", None):
        with patch.object(
            Archive, "_get_default_output_dir", return_value=missing
        ):
            integration.open_folder(None)
            mock_warning.assert_called_once()
            args = mock_warning.call_args[1]
            assert "Folder Not Found" in args["message"]


def test_open_folder_missing_folder(
    missing_folder: Path, mock_warning: MagicMock
) -> None:
    """Verify that a warning is shown for nonexistent folders."""
    integration.open_folder(missing_folder)
    mock_warning.assert_called_once()
    args = mock_warning.call_args[1]
    assert "Folder Not Found" in args["message"]


@pytest.mark.parametrize(
    "system_name, expected_call",
    [
        ("windows", "os.startfile"),
        ("darwin", "subprocess.call"),
        ("linux", "subprocess.run"),
    ],
)
def test_open_folder_platform_calls(
    temp_folder: Path,
    system_name: str,
    expected_call: str,
) -> None:
    """Verify the correct OS-specific opening function is called."""
    folder = temp_folder
    with patch("platform.system", return_value=system_name):
        if expected_call == "os.startfile":
            with patch("os.startfile", create=True) as mock_start:
                integration._open_folder_platform(folder)
                mock_start.assert_called_once_with(folder)
        elif expected_call == "subprocess.call":
            with patch("subprocess.call") as mock_sub:
                integration._open_folder_platform(folder)
                mock_sub.assert_called_once()
                assert str(folder) in mock_sub.call_args[0][0]
        else:  # subprocess.run via threading
            with patch("subprocess.run") as mock_run:
                with patch("threading.Thread") as mock_thread_class:
                    # Capture the target function passed to Thread
                    mock_thread_instance = MagicMock()
                    mock_thread_class.return_value = mock_thread_instance

                    integration._open_folder_platform(folder)

                    # Verify thread was created and started
                    mock_thread_class.assert_called_once()
                    mock_thread_instance.start.assert_called_once()

                    # Extract the target and run it synchronously
                    target = mock_thread_class.call_args[1].get("target")
                    if target:
                        target()

                    mock_run.assert_called_once()
                    assert str(folder) in mock_run.call_args[0][0]


def test_open_folder_handles_exception(
    temp_folder: Path, mock_warning: MagicMock
) -> None:
    """Verify exception handling during folder opening."""
    with patch(
        "atlas.lib.integration._open_folder_platform",
        side_effect=Exception("Boom"),
    ):
        integration.open_folder(temp_folder)
        mock_warning.assert_called_once()
        args = mock_warning.call_args[1]
        assert "Failed to Open Folder" in args["message"]


# =============================================================================
# TESTS — Linux Desktop Environment and Candidate Handlers
# =============================================================================


def test_get_clean_desktop_environment_restores_ld_library_path_orig(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify LD_LIBRARY_PATH_ORIG is restored to LD_LIBRARY_PATH."""
    monkeypatch.setenv("LD_LIBRARY_PATH", "/tmp/_MEI12345")
    monkeypatch.setenv("LD_LIBRARY_PATH_ORIG", "/usr/lib:/usr/local/lib")
    clean = integration._get_clean_desktop_environment()
    assert clean["LD_LIBRARY_PATH"] == "/usr/lib:/usr/local/lib"
    assert "LD_LIBRARY_PATH_ORIG" not in clean


def test_get_clean_desktop_environment_removes_qt_and_gio_overrides(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify Qt, GIO, and AT bridge overrides are removed."""
    monkeypatch.setenv("LD_LIBRARY_PATH", "/tmp/_MEI12345")
    monkeypatch.delenv("LD_LIBRARY_PATH_ORIG", raising=False)
    monkeypatch.setenv("QT_PLUGIN_PATH", "/tmp/_MEI12345/plugins")
    monkeypatch.setenv(
        "QT_QPA_PLATFORM_PLUGIN_PATH", "/tmp/_MEI12345/platforms"
    )
    monkeypatch.setenv("QT_QPA_PLATFORM", "xcb")
    monkeypatch.setenv("QT_STYLE_OVERRIDE", "fusion")
    monkeypatch.setenv("QML_IMPORT_PATH", "/tmp/_MEI12345/qml")
    monkeypatch.setenv("QML2_IMPORT_PATH", "/tmp/_MEI12345/qml")
    monkeypatch.setenv("GIO_MODULE_DIR", "")
    monkeypatch.setenv("NO_AT_BRIDGE", "1")

    clean = integration._get_clean_desktop_environment()
    assert "LD_LIBRARY_PATH" not in clean
    assert "QT_PLUGIN_PATH" not in clean
    assert "QT_QPA_PLATFORM_PLUGIN_PATH" not in clean
    assert "QT_QPA_PLATFORM" not in clean
    assert "QT_STYLE_OVERRIDE" not in clean
    assert "QML_IMPORT_PATH" not in clean
    assert "QML2_IMPORT_PATH" not in clean
    assert "GIO_MODULE_DIR" not in clean
    assert "NO_AT_BRIDGE" not in clean


def test_get_clean_desktop_environment_frozen_removes_python_overrides(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify frozen Python variables are stripped when frozen."""
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setenv("PYTHONPATH", "/tmp/_MEI12345")
    monkeypatch.setenv("PYTHONHOME", "/tmp/_MEI12345")
    monkeypatch.setenv("_MEIPASS2", "/tmp/_MEI12345")

    clean = integration._get_clean_desktop_environment()
    assert "PYTHONPATH" not in clean
    assert "PYTHONHOME" not in clean
    assert "_MEIPASS2" not in clean


def test_is_kde_true(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify _is_kde returns True for KDE sessions."""
    monkeypatch.setenv("XDG_CURRENT_DESKTOP", "KDE")
    monkeypatch.delenv("KDE_SESSION_VERSION", raising=False)
    assert integration._is_kde() is True

    monkeypatch.delenv("XDG_CURRENT_DESKTOP", raising=False)
    monkeypatch.setenv("KDE_SESSION_VERSION", "6")
    assert integration._is_kde() is True


def test_is_kde_false(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify _is_kde returns False for non-KDE sessions."""
    monkeypatch.setenv("XDG_CURRENT_DESKTOP", "GNOME")
    monkeypatch.delenv("KDE_SESSION_VERSION", raising=False)
    monkeypatch.delenv("DESKTOP_SESSION", raising=False)
    monkeypatch.delenv("XDG_SESSION_DESKTOP", raising=False)
    assert integration._is_kde() is False


def test_get_linux_file_manager_candidates_kde(
    temp_folder: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify KDE candidates include dolphin and kde-open tools."""
    monkeypatch.setenv("XDG_CURRENT_DESKTOP", "KDE")
    monkeypatch.delenv("KDE_SESSION_VERSION", raising=False)
    candidates = integration._get_linux_file_manager_candidates(temp_folder)
    exes = [cmd[0] for cmd in candidates]
    assert exes[0] == "xdg-open"
    assert "dolphin" in exes
    assert "kde-open6" in exes
    assert "kioclient6" in exes


def test_get_linux_file_manager_candidates_non_kde(
    temp_folder: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify generic candidates for non-KDE environments."""
    monkeypatch.setenv("XDG_CURRENT_DESKTOP", "GNOME")
    monkeypatch.delenv("KDE_SESSION_VERSION", raising=False)
    candidates = integration._get_linux_file_manager_candidates(temp_folder)
    exes = [cmd[0] for cmd in candidates]
    assert exes[0] == "xdg-open"
    assert "nautilus" in exes
    assert "gio" in exes


def test_run_linux_open_kde_fallback(
    temp_folder: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify fallback to dolphin when xdg-open fails on KDE Plasma."""
    monkeypatch.setenv("XDG_CURRENT_DESKTOP", "KDE")

    def fake_which(
        cmd: str, path: Optional[str] = None
    ) -> Optional[str]:
        if cmd == "dolphin":
            return "/usr/bin/dolphin"
        return None

    monkeypatch.setattr("shutil.which", fake_which)

    fail_process = subprocess.CompletedProcess(
        args=["xdg-open", str(temp_folder)],
        returncode=2,
        stdout="",
        stderr="Failed to launch",
    )
    success_process = subprocess.CompletedProcess(
        args=["dolphin", str(temp_folder)],
        returncode=0,
        stdout="",
        stderr="",
    )

    calls = []

    def fake_run(
        cmd: List[str], **kwargs: object
    ) -> subprocess.CompletedProcess:
        calls.append(cmd)
        if cmd[0] == "xdg-open":
            return fail_process
        if cmd[0] == "dolphin":
            return success_process
        return fail_process

    monkeypatch.setattr("subprocess.run", fake_run)

    result = integration._run_linux_open(temp_folder)
    assert result is True
    assert len(calls) == 2
    assert calls[0][0] == "xdg-open"
    assert calls[1][0] == "dolphin"


def test_run_linux_open_all_fail(
    temp_folder: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify _run_linux_open returns False when all candidates fail."""
    monkeypatch.setattr("shutil.which", lambda *args, **kwargs: None)
    fail_process = subprocess.CompletedProcess(
        args=["xdg-open", str(temp_folder)],
        returncode=1,
        stdout="",
        stderr="Error",
    )
    monkeypatch.setattr(
        "subprocess.run", lambda *args, **kwargs: fail_process
    )

    result = integration._run_linux_open(temp_folder)
    assert result is False


def test_is_tiling_window_manager_swaysock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify True when SWAYSOCK is present on Linux."""
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv("SWAYSOCK", "/run/user/1000/sway-ipc.sock")
    assert integration._is_tiling_window_manager() is True


def test_is_tiling_window_manager_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify True when session desktop names a tiling WM."""
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.delenv("SWAYSOCK", raising=False)
    monkeypatch.setenv("XDG_CURRENT_DESKTOP", "i3")
    assert integration._is_tiling_window_manager() is True


def test_is_tiling_window_manager_false(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify False on floating desktops like GNOME or KDE."""
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.delenv("SWAYSOCK", raising=False)
    monkeypatch.setenv("XDG_CURRENT_DESKTOP", "GNOME")
    monkeypatch.delenv("XDG_SESSION_DESKTOP", raising=False)
    monkeypatch.delenv("DESKTOP_SESSION", raising=False)
    assert integration._is_tiling_window_manager() is False


def test_is_tiling_window_manager_non_linux(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify False on non-Linux platforms."""
    monkeypatch.setattr(sys, "platform", "win32")
    assert integration._is_tiling_window_manager() is False


# =============================================================================
# TEST EXECUTION
# =============================================================================

if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
