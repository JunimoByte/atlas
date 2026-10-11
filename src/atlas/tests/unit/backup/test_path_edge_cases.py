"""Atlas | Tests | Backup | Path Edge Cases.

Security and robustness tests for path traversal, exotic filenames,
directory hierarchies, and timestamp normalization across operating systems.
"""

# =============================================================================
# IMPORTS
# =============================================================================

import zipfile
from pathlib import Path
from typing import Generator, Tuple
from unittest.mock import MagicMock

import pytest

from atlas.backup import archive
from atlas.backup.attribute import create_zip_info, safe_zipinfo_date

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def path_env(tmp_path: Path) -> Generator[Tuple[Path, Path, Path], None, None]:
    """Provide isolated source, output, and restore directories."""
    source_dir = tmp_path / "path_profile"
    source_dir.mkdir(parents=True, exist_ok=True)
    dest_dir = tmp_path / "path_output"
    dest_dir.mkdir(parents=True, exist_ok=True)
    restore_dir = tmp_path / "path_restore"
    restore_dir.mkdir(parents=True, exist_ok=True)

    archive.set_zip_output_dir(dest_dir)
    try:
        yield source_dir, dest_dir, restore_dir
    finally:
        archive.set_zip_output_dir(None)


# =============================================================================
# TESTS — Path Traversal Rejection
# =============================================================================


@pytest.mark.parametrize(
    "malicious_name",
    [
        "../escaped.zip",
        "../../escaped.zip",
        "nested/../../escaped.zip",
        "dir/../../../etc/shadow.zip",
        "..\\escaped_win.zip",
        "..\\..\\escaped_win.zip",
    ],
)
def test_path_traversal_zip_name_rejected(
    path_env: Tuple[Path, Path, Path], malicious_name: str
) -> None:
    """Verify archive path resolution rejects traversal escape attempts."""
    with pytest.raises(ValueError) as exc_info:
        archive._resolve_output_zip_path(malicious_name)
    assert "escapes the output directory" in str(exc_info.value)


def test_valid_zip_name_resolved_inside_output_dir(
    path_env: Tuple[Path, Path, Path],
) -> None:
    """Verify valid archive names resolve strictly inside output directory."""
    _, dest_dir, _ = path_env
    resolved = archive._resolve_output_zip_path("valid_backup.zip")
    assert resolved == (dest_dir / "valid_backup.zip").resolve()


# =============================================================================
# TESTS — Exotic Filenames & Non-ASCII Characters
# =============================================================================


def test_exotic_filenames_archive_roundtrip(
    path_env: Tuple[Path, Path, Path],
) -> None:
    """Verify non-ASCII, spaces, and multi-dot filenames preserve contents."""
    source_dir, _, restore_dir = path_env

    exotic_files = {
        "bookmark_🔥_sync.json": "fire sync",
        "мои_закладки.db": "cyrillic text",
        "café_au_lait.sqlite": "accented text",
        "file with   multiple spaces.log": "space text",
        ".hidden_profile_dot": "hidden file",
        "archive..v1...data.bin": "multi dot",
    }

    for filename, content in exotic_files.items():
        (source_dir / filename).write_text(content, encoding="utf-8")

    zip_path = archive.compress([source_dir], zip_name="exotic.zip")
    assert zip_path is not None
    assert zip_path.is_file()

    with zipfile.ZipFile(zip_path, "r") as zf:
        assert zf.testzip() is None
        zf.extractall(restore_dir)

    extracted_root = restore_dir / source_dir.name
    for filename, content in exotic_files.items():
        extracted_file = extracted_root / filename
        assert extracted_file.is_file(), f"Missing extracted {filename}"
        assert (
            extracted_file.read_text(encoding="utf-8") == content
        ), f"Content mismatch in {filename}"


# =============================================================================
# TESTS — Deep Hierarchy & Path Standards
# =============================================================================


def test_deep_directory_hierarchy_and_forward_slashes(
    path_env: Tuple[Path, Path, Path],
) -> None:
    """Verify deeply nested directories format with forward slashes in ZIP."""
    source_dir, _, restore_dir = path_env

    deep_path = source_dir
    for level in range(1, 11):
        deep_path = deep_path / f"level_{level}"
    deep_path.mkdir(parents=True, exist_ok=True)
    target_file = deep_path / "deep_leaf.txt"
    target_file.write_text("deep payload", encoding="utf-8")

    zip_path = archive.compress([source_dir], zip_name="deep_hierarchy.zip")
    assert zip_path is not None

    with zipfile.ZipFile(zip_path, "r") as zf:
        assert zf.testzip() is None
        for info in zf.infolist():
            # ZIP specification strictly requires '/' regardless of OS
            assert "\\" not in info.filename
        zf.extractall(restore_dir)

    extracted_leaf = (
        restore_dir
        / source_dir.name
        / Path(*[f"level_{lvl}" for lvl in range(1, 11)])
        / "deep_leaf.txt"
    )
    assert extracted_leaf.is_file()
    assert extracted_leaf.read_text(encoding="utf-8") == "deep payload"


# =============================================================================
# TESTS — Timestamp Normalization
# =============================================================================


def test_safe_zipinfo_date_clamps_pre_1980_and_future_dates(
    tmp_path: Path,
) -> None:
    """Verify safe_zipinfo_date clamps dates to ZIP format constraints."""
    dummy_file = tmp_path / "timestamp_test.txt"
    dummy_file.write_text("test", encoding="utf-8")

    # Epoch 0 (1970-01-01) must clamp to >= 1980
    date_epoch = safe_zipinfo_date(dummy_file, mtime=0.0)
    assert date_epoch[0] >= 1980

    # Negative mtime must clamp to >= 1980
    date_negative = safe_zipinfo_date(dummy_file, mtime=-1000.0)
    assert date_negative[0] >= 1980

    # Far future date (> 2107) must clamp to <= 2107
    date_future = safe_zipinfo_date(dummy_file, mtime=5000000000.0)
    assert date_future[0] <= 2107

    # Missing file / OSError must return fallback 1980-01-01
    missing_file = tmp_path / "does_not_exist.txt"
    fallback_date = safe_zipinfo_date(missing_file)
    assert fallback_date == (1980, 1, 1, 0, 0, 0)


def test_create_zip_info_handles_inaccessible_file(
    tmp_path: Path,
) -> None:
    """Verify create_zip_info succeeds even if file stat raises OSError."""
    target_file = tmp_path / "inaccessible.dat"
    target_file.write_text("data", encoding="utf-8")

    mock_stat = MagicMock(side_effect=OSError("Access denied"))
    with pytest.MonkeyPatch().context() as mp:
        mp.setattr(Path, "stat", mock_stat)
        zi = create_zip_info(target_file)
        assert zi.date_time == (1980, 1, 1, 0, 0, 0)
        assert zi.compress_type == zipfile.ZIP_DEFLATED
