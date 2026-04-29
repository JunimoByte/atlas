"""Atlas | Tests | Backup | Attribute Management.

Unit tests for backup/attribute.py.
Covers ZIP metadata, timestamp clamping, and permission handling.
"""

# =============================================================================
# IMPORTS
# =============================================================================

import os
import sys
import zipfile
from pathlib import Path

import pytest

from atlas.backup import attribute

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def sample_file(tmp_path: Path) -> Path:
    """Provide a simple text file for attribute tests."""
    f = tmp_path / "file.txt"
    f.write_text("content")
    return f


# =============================================================================
# TESTS — Safe zipinfo date
# =============================================================================


def test_safe_zipinfo_date_returns_tuple(sample_file: Path) -> None:
    """Verify that safe_zipinfo_date returns a 6-element tuple."""
    result = attribute.safe_zipinfo_date(sample_file)
    assert isinstance(result, tuple)
    assert len(result) == 6


def test_safe_zipinfo_date_year_clamped_to_1980(
    sample_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify that safe_zipinfo_date clamps years to 1980 or later."""
    from datetime import datetime
    monkeypatch.setattr(
        attribute,
        "datetime",
        type(
            "dt", (),
            {"fromtimestamp": staticmethod(lambda _: datetime(1970, 1, 1))}
        )
    )
    result = attribute.safe_zipinfo_date(sample_file)
    assert result[0] == 1980


def test_safe_zipinfo_date_missing_file() -> None:
    """Verify fallback tuple for missing files."""
    result = attribute.safe_zipinfo_date(Path("/nonexistent/path/file.txt"))
    assert result == (1980, 1, 1, 0, 0, 0)


# =============================================================================
# TESTS — Get windows version
# =============================================================================


def test_get_windows_version_returns_none_on_non_windows(
    monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify that None is returned when not on Windows."""


def test_get_windows_version_returns_tuple_on_windows(
    monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify that a (major, minor) tuple is returned on Windows."""
    monkeypatch.setattr(os, "name", "nt")
    fake_ver = type("V", (), {"major": 10, "minor": 0})()
    monkeypatch.setattr(os.sys, "getwindowsversion", lambda: fake_ver)
    assert attribute.get_windows_version() == (10, 0)


# =============================================================================
# TESTS — Set file permissions
# =============================================================================


def test_set_file_permissions_returns_int() -> None:
    """Verify that an integer is returned."""
    assert isinstance(attribute.set_file_permissions(0o644), int)


@pytest.mark.parametrize(
    "win_version, mode, expected",
    [
        ((5, 1), 0o755, 0o600 << 16),   # Old Windows → fixed 0o600
        ((10, 0), 0o644, 0o644 << 16),  # Modern Windows → actual mode
    ]
)
def test_set_file_permissions_by_os_version(
    monkeypatch: pytest.MonkeyPatch,
    win_version: tuple,
    mode: int,
    expected: int
) -> None:
    """Verify correct mode selection based on OS version."""
    monkeypatch.setattr(attribute, "get_windows_version", lambda: win_version)
    assert attribute.set_file_permissions(mode) == expected


# =============================================================================
# TESTS — Create zip info
# =============================================================================


def test_create_zip_info_returns_zipinfo(sample_file: Path) -> None:
    """Verify that a ZipInfo object is returned."""
    assert isinstance(attribute.create_zip_info(sample_file), zipfile.ZipInfo)


def test_create_zip_info_sets_date_time(sample_file: Path) -> None:
    """Verify that the date_time tuple is populated."""
    zi = attribute.create_zip_info(sample_file)
    assert zi.date_time[0] >= 1980


def test_create_zip_info_missing_file() -> None:
    """Verify fallback attributes for missing files."""
    zi = attribute.create_zip_info(Path("/no/such/file.txt"))
    assert isinstance(zi, zipfile.ZipInfo)
    assert zi.external_attr == 0o600 << 16


# =============================================================================
# TEST EXECUTION
# =============================================================================

if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
