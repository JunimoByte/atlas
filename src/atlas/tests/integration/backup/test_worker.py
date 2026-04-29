"""Atlas | Tests | Backup | Worker Integration.

Integration tests ensuring the Worker orchestrates the Pipeline accurately
and communicates correctly via PyQt signals.
"""

# =============================================================================
# IMPORTS
# =============================================================================

import sys
import zipfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

import atlas.backup.archive
import atlas.backup.size
import atlas.backup.worker
import atlas.lib.browsers
from atlas.backup.worker import Worker

# =============================================================================
# FIXTURES & MOCKS
# =============================================================================


@pytest.fixture
def temp_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Set up a temporary filesystem and patch output directories."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    # Patch output dir
    monkeypatch.setattr(
        atlas.backup.archive, "ZIP_OUTPUT_DIR", output_dir
    )
    monkeypatch.setattr(
        atlas.backup.archive, "get_zip_output_dir", lambda: output_dir
    )

    def mock_check_disk_space(size_bytes):
        """Mock disk space check to always return True."""
        return (True, "100 GB")

    monkeypatch.setattr(
        atlas.backup.size, "check_disk_space", mock_check_disk_space
    )

    monkeypatch.setattr(
        atlas.lib.browsers, "grab", lambda: {"PytestBrowser": {}}
    )

    # Setup mock profile with dummy files
    profile_path = tmp_path / "PytestBrowser" / "Profile 1"
    profile_path.mkdir(parents=True)
    (profile_path / "Bookmarks").write_text("dummy bookmarks")
    (profile_path / "History").write_text("dummy history")

    # Patch Profile.find_profile so we don't scan real OS drives
    def mock_find_profile(browser_name, os_name, browsers_data):
        """Mock profile search to return the dummy path."""
        if browser_name == "PytestBrowser":
            return [str(profile_path)]
        return []

    monkeypatch.setattr(
        "atlas.backup.profile.find_profile", mock_find_profile
    )

    return output_dir


# =============================================================================
# TESTS — Worker Integration
# =============================================================================


def test_worker_integration_success(temp_environment: Path):
    """Execute the full backup pipeline successfully.

    Emits the expected progression of UI signals and creates the ZIP.
    """
    worker = Worker()

    # Connect signal mocks
    mock_progress = MagicMock()
    mock_done = MagicMock()
    mock_estimated_size = MagicMock()
    mock_scanned_entries = MagicMock()
    mock_disk_space_error = MagicMock()
    mock_no_browsers_found = MagicMock()
    mock_cancelled = MagicMock()

    worker.progress.connect(mock_progress)
    worker.done.connect(mock_done)
    worker.estimated_size.connect(mock_estimated_size)
    worker.scanned_entries.connect(mock_scanned_entries)
    worker.disk_space_error.connect(mock_disk_space_error)
    worker.no_browsers_found.connect(mock_no_browsers_found)
    worker.cancelled.connect(mock_cancelled)

    # Check signals
    worker.run()

    assert mock_scanned_entries.called
    mock_estimated_size.assert_called_once()
    mock_progress.assert_called_with(1, 1)
    mock_done.assert_called_once()

    mock_disk_space_error.assert_not_called()
    mock_no_browsers_found.assert_not_called()
    mock_cancelled.assert_not_called()

    # Verify ZIP output
    zip_path = temp_environment / "PytestBrowser.zip"
    assert zip_path.exists(), "Wait, why wasn't the ZIP file created?"
    with zipfile.ZipFile(zip_path, "r") as zf:
        names = zf.namelist()
        assert any(name.endswith("Bookmarks") for name in names)
        assert any(name.endswith("History") for name in names)


def test_worker_integration_no_browsers(monkeypatch: pytest.MonkeyPatch):
    """Worker should properly abort and signal when no profiles exist."""
    worker = Worker()

    # Mock find_profile to return an empty list
    import atlas.backup.profile
    monkeypatch.setattr(
        atlas.backup.profile, "find_profile", lambda b, o, d: []
    )
    monkeypatch.setattr(
        atlas.lib.browsers, "grab", lambda: {"EmptyBrowser": {}}
    )

    mock_no_browsers_found = MagicMock()
    mock_done = MagicMock()

    worker.no_browsers_found.connect(mock_no_browsers_found)
    worker.done.connect(mock_done)

    worker.run()

    mock_no_browsers_found.assert_called_once()
    mock_done.assert_not_called()


# =============================================================================
# TEST EXECUTION
# =============================================================================

if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
