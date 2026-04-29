"""Atlas | Tests | Backup | Filter Management.

Unit tests for backup/filter.py.
Covers blacklist, symlink exclusion, cancellation, and file scanning.
"""

# =============================================================================
# IMPORTS
# =============================================================================

import os
import sys
from pathlib import Path

import pytest

import atlas.backup.filter as backup_filter
from atlas.backup.filter import scan_files

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture(autouse=True)
def clean_blacklists(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reset blacklist globals to known values before each test."""
    monkeypatch.setattr(
        backup_filter, "SKIP_FOLDERS", {"__pycache__", "skip_me"}
    )
    monkeypatch.setattr(backup_filter, "SKIP_FILE_EXTENSION", {".log", ".tmp"})
    monkeypatch.setattr(backup_filter, "SKIP_FILE_WITH_EXTENSION", {
        ".db": {"Cookies", "History"}
    })


def make_file(path: Path, content: str = "data") -> Path:
    """Create a file at *path* with the given *content*, creating parent dirs.

    Args:
        path: The full path of the file to create.
        content: The text to write into the file.

    Returns:
        The ``Path`` of the created file.

    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


# =============================================================================
# TESTS — basic scanning
# =============================================================================


def test_scan_files_returns_valid_files(tmp_path: Path) -> None:
    """Verify that regular, non-blacklisted files are scanned."""
    make_file(tmp_path / "profile.json")
    make_file(tmp_path / "data.txt")
    results = scan_files([tmp_path])
    names = [f.name for f in results]
    assert "profile.json" in names
    assert "data.txt" in names


def test_scan_files_excludes_blacklisted_extension(tmp_path: Path) -> None:
    """Verify that blacklisted extensions are skipped."""
    make_file(tmp_path / "debug.log")
    make_file(tmp_path / "temp.tmp")
    results = scan_files([tmp_path])
    names = [f.name for f in results]
    assert "debug.log" not in names
    assert "temp.tmp" not in names


def test_scan_files_excludes_blacklisted_folder(tmp_path: Path) -> None:
    """Verify that blacklisted folders are skipped."""
    make_file(tmp_path / "__pycache__" / "module.pyc")
    make_file(tmp_path / "skip_me" / "data.txt")
    make_file(tmp_path / "keep" / "profile.json")
    results = scan_files([tmp_path])
    names = [f.name for f in results]
    assert "module.pyc" not in names
    assert "profile.json" in names


def test_scan_files_excludes_named_file_with_extension(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify that specific name + extension pairs are skipped."""
    monkeypatch.setattr(backup_filter, "SKIP_FILE_WITH_EXTENSION", {
        ".db": {"Cookies.db", "History.db"}
    })
    make_file(tmp_path / "Cookies.db")   # full name in blacklist → skip
    make_file(tmp_path / "Cookies.txt")  # different extension → keep
    make_file(tmp_path / "Other.db")     # .db ext but name not in set → keep

    results = scan_files([tmp_path])
    names = [f.name for f in results]

    assert "Cookies.db" not in names
    assert "Cookies.txt" in names
    assert "Other.db" in names


def test_scan_files_returns_empty_for_empty_directory(tmp_path: Path) -> None:
    """Verify that empty directories return no files."""
    assert scan_files([tmp_path]) == []


def test_scan_files_handles_multiple_sources(tmp_path: Path) -> None:
    """Verify that all source directories are scanned."""
    src_a = tmp_path / "a"
    src_b = tmp_path / "b"
    src_a.mkdir()
    src_b.mkdir()
    make_file(src_a / "file_a.txt")
    make_file(src_b / "file_b.txt")
    results = scan_files([src_a, src_b])
    names = [f.name for f in results]
    assert "file_a.txt" in names
    assert "file_b.txt" in names


# =============================================================================
# TESTS — cancellation
# =============================================================================


def test_scan_files_respects_cancel_callback(tmp_path: Path) -> None:
    """Verify that scanning stops when cancelled."""
    make_file(tmp_path / "file.txt")
    assert scan_files([tmp_path], cancel_callback=lambda: True) == []


def test_scan_files_continues_when_cancel_is_false(tmp_path: Path) -> None:
    """Verify that scanning proceeds when not cancelled."""
    make_file(tmp_path / "file.txt")
    results = scan_files([tmp_path], cancel_callback=lambda: False)
    assert len(results) >= 1


# =============================================================================
# TEST EXECUTION
# =============================================================================

if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
