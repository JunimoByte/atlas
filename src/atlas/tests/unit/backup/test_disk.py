"""Atlas | Tests | Backup | Filesystem Utilities.

Unit tests for backup/disk.py.
Covers safe file deletion, base path resolution, and ZIP path sanitization.
"""

# =============================================================================
# IMPORTS
# =============================================================================

import sys
from pathlib import Path

import pytest

from atlas.backup import disk

# =============================================================================
# TESTS — Safe unlink
# =============================================================================


def test_safe_unlink_deletes_existing_file(tmp_path: Path) -> None:
    """Verify that safe_unlink deletes an existing file."""
    f = tmp_path / "file.txt"
    f.write_text("data")
    disk.safe_unlink(f)
    assert not f.exists()


def test_safe_unlink_does_not_raise_on_missing_file(tmp_path: Path) -> None:
    """Verify that safe_unlink does not raise on missing files."""
    disk.safe_unlink(tmp_path / "ghost.txt")


# =============================================================================
# TESTS — Find base path
# =============================================================================


def test_find_base_path_finds_correct_source(tmp_path: Path) -> None:
    """Verify that the source containing the file is returned."""
    source_a = tmp_path / "a"
    source_b = tmp_path / "b"
    source_a.mkdir()
    source_b.mkdir()
    file_path = source_a / "sub" / "file.txt"
    file_path.parent.mkdir()
    file_path.write_text("data")

    result = disk.find_base_path(file_path, [source_a, source_b])
    assert result == source_a


def test_find_base_path_returns_none_when_no_match(tmp_path: Path) -> None:
    """Verify that None is returned if no source matches."""
    source = tmp_path / "source"
    source.mkdir()
    unrelated = tmp_path / "other" / "file.txt"
    assert disk.find_base_path(unrelated, [source]) is None


def test_find_base_path_empty_sources(tmp_path: Path) -> None:
    """Verify that None is returned for an empty sources list."""
    assert disk.find_base_path(tmp_path / "file.txt", []) is None


# =============================================================================
# TESTS — Relative path
# =============================================================================


@pytest.fixture
def zipped_file(tmp_path: Path) -> tuple:
    """Return a (file, base) pair ready for relative_zip_path tests."""
    base = tmp_path / "source"
    base.mkdir()
    f = base / "sub" / "file.txt"
    f.parent.mkdir()
    f.write_text("data")
    return f, base


def test_relative_zip_path(zipped_file: tuple) -> None:
    """Verify forward slashes, base prefix, and lack of NUL bytes."""
    f, base = zipped_file
    result = disk.relative_zip_path(f, base)
    assert "/" in result
    assert "\\" not in result
    assert result.startswith("source/")
    assert "\x00" not in result


# =============================================================================
# TEST EXECUTION
# =============================================================================

if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
