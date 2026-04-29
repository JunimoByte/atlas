"""Atlas | Tests | Backup | Pipeline Integration.

Integration tests ensuring Pipeline.perform_backup accurately uses
archive.compress to create a ZIP file with the correct contents.
"""

# =============================================================================
# IMPORTS
# =============================================================================

import sys
import zipfile
from pathlib import Path

import pytest

import atlas.backup.archive
import atlas.lib.browsers
from atlas.backup.pipeline import Pipeline

# =============================================================================
# TESTS — Pipeline Integration
# =============================================================================


def test_pipeline_integration_creates_zip(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Pipeline should create a ZIP containing the mocked browser profile."""
    # Setup mock zip output
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    monkeypatch.setattr(atlas.backup.archive, "ZIP_OUTPUT_DIR", output_dir)
    monkeypatch.setattr(
        atlas.lib.browsers, "grab", lambda: {"FakeBrowser": {}}
    )

    # Setup mock profile path
    profile_path = tmp_path / "FakeBrowser" / "Profile 1"
    profile_path.mkdir(parents=True)

    # Create some dummy files to zip
    (profile_path / "Bookmarks").write_text("dummy bookmarks content")
    (profile_path / "History").write_text("dummy history content")

    extensions_dir = profile_path / "Extensions"
    extensions_dir.mkdir()
    (extensions_dir / "ext1.txt").write_text("extension code")

    pipeline = Pipeline()
    browser_matches = {"FakeBrowser": [str(profile_path)]}
    pipeline.perform_backup(browser_matches)

    # check if the zip exists and has the right files
    zip_path = output_dir / "FakeBrowser.zip"
    with zipfile.ZipFile(zip_path, "r") as zf:
        names = zf.namelist()

        assert any(name.endswith("Bookmarks") for name in names)
        assert any(name.endswith("History") for name in names)
        assert any(name.endswith("ext1.txt") for name in names)

        bookmarks_entry = next(
            name for name in names if name.endswith("Bookmarks")
        )
        with zf.open(bookmarks_entry) as f:
            assert f.read() == b"dummy bookmarks content"


# =============================================================================
# TEST EXECUTION
# =============================================================================

if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
