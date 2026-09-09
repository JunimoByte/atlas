"""Atlas | Tests | Packages | Integration.

Unit tests for integration.py OS folder helpers.
"""

# =============================================================================
# IMPORTS
# =============================================================================

import sys
from pathlib import Path
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
    """Verify fallback to ZIP_OUTPUT_DIR when it has been set by a prior run."""
    fake_dir = tmp_path / "archive_dir"
    fake_dir.mkdir()
    with patch.object(Archive, "ZIP_OUTPUT_DIR", fake_dir):
        with patch("atlas.lib.integration._open_folder_platform") as mock_open:
            integration.open_folder(None)
            mock_open.assert_called_once_with(fake_dir)


def test_open_folder_none_uses_default_output_dir(
    tmp_path: Path,
) -> None:
    """Verify fallback to _get_default_output_dir when ZIP_OUTPUT_DIR is None."""
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
    """Verify that a warning is shown if no path resolves to an existing folder."""
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
# TEST EXECUTION
# =============================================================================

if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
