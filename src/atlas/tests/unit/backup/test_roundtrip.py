"""Atlas | Tests | Backup | Round-trip.

Synthetic unmocked round-trip backup and verification tests.
Validates real filesystem archive creation, CRC integrity, and extraction.
"""

# =============================================================================
# IMPORTS
# =============================================================================

import hashlib
import os
import zipfile
from pathlib import Path
from typing import Dict, Generator, Tuple
from unittest.mock import patch

import pytest

from atlas.backup import archive
from atlas.backup.pipeline import Pipeline, PipelineResult

# =============================================================================
# HELPERS
# =============================================================================


def _sha256(path: Path) -> str:
    """Return SHA-256 hex digest for a file."""
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        while True:
            chunk = stream.read(65536)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def roundtrip_env(
    tmp_path: Path,
) -> Generator[Tuple[Path, Path, Path, Dict[str, str]], None, None]:
    """Create isolated source, destination, and restore directories."""
    source_dir = tmp_path / "synthetic_profile"
    source_dir.mkdir(parents=True, exist_ok=True)
    dest_dir = tmp_path / "backup_dest"
    dest_dir.mkdir(parents=True, exist_ok=True)
    restore_dir = tmp_path / "restore_dest"
    restore_dir.mkdir(parents=True, exist_ok=True)

    # Populate realistic synthetic browser profile files
    (source_dir / "Preferences").write_text(
        '{"browser":{"show_home_button":true}}', encoding="utf-8"
    )
    (source_dir / "Bookmarks").write_text(
        '{"checksum":"abc123","roots":{"bookmark_bar":{"children":[]}}}',
        encoding="utf-8",
    )
    (source_dir / "Cookies").write_bytes(
        b"SQLite format 3\x00\x10\x00\x01\x01\x00" + b"\xaa" * 512
    )

    nested = source_dir / "IndexedDB" / "https_example_0.indexeddb.leveldb"
    nested.mkdir(parents=True, exist_ok=True)
    (nested / "000003.log").write_bytes(os.urandom(4096))
    (nested / "CURRENT").write_text("MANIFEST-000001\n", encoding="utf-8")
    (nested / "empty_marker.dat").write_bytes(b"")

    unicode_file = source_dir / "Extensions" / "accent_é_test.json"
    unicode_file.parent.mkdir(parents=True, exist_ok=True)
    unicode_file.write_text('{"name":"café"}', encoding="utf-8")

    expected_hashes: Dict[str, str] = {}
    for root, _, files in os.walk(str(source_dir)):
        for name in files:
            file_path = Path(root) / name
            rel = file_path.relative_to(source_dir).as_posix()
            expected_hashes[rel] = _sha256(file_path)

    archive.set_zip_output_dir(dest_dir)
    try:
        yield source_dir, dest_dir, restore_dir, expected_hashes
    finally:
        archive.set_zip_output_dir(None)


# =============================================================================
# TESTS — Unmocked Round-Trip
# =============================================================================


def test_unmocked_compress_creates_valid_extractable_archive(
    roundtrip_env: Tuple[Path, Path, Path, Dict[str, str]],
) -> None:
    """Verify archive.compress produces a bit-perfect, extractable ZIP."""
    source_dir, dest_dir, restore_dir, expected_hashes = roundtrip_env

    zip_path = archive.compress([source_dir], zip_name="roundtrip.zip")
    assert zip_path is not None
    assert zip_path.exists()
    assert zip_path.stat().st_size > 22

    # Verify standard ZIP structure and CRC integrity
    assert zipfile.is_zipfile(zip_path)
    with zipfile.ZipFile(zip_path, "r") as zf:
        crc_error = zf.testzip()
        assert crc_error is None, f"CRC check failed on {crc_error}"

        # Verify deflate compression and forward-slash path standard
        for info in zf.infolist():
            assert info.compress_type == zipfile.ZIP_DEFLATED
            assert "\\" not in info.filename

        zf.extractall(restore_dir)

    # Verify extracted contents match original source files exactly
    extracted_root = restore_dir / source_dir.name
    assert extracted_root.is_dir()

    extracted_hashes: Dict[str, str] = {}
    for root, _, files in os.walk(str(extracted_root)):
        for name in files:
            file_path = Path(root) / name
            rel = file_path.relative_to(extracted_root).as_posix()
            extracted_hashes[rel] = _sha256(file_path)

    assert extracted_hashes == expected_hashes


def test_unmocked_pipeline_roundtrip_execution(
    roundtrip_env: Tuple[Path, Path, Path, Dict[str, str]],
) -> None:
    """Verify full Pipeline executes unmocked and produces valid archives."""
    source_dir, dest_dir, restore_dir, expected_hashes = roundtrip_env

    pipeline = Pipeline()
    with patch.object(
        pipeline,
        "scan_profiles",
        return_value={"SyntheticBrowser": [str(source_dir)]},
    ):
        result = pipeline.run()

    assert result == PipelineResult.SUCCESS
    created_archives = pipeline.created_archives
    assert len(created_archives) == 1

    archive_path = Path(created_archives[0])
    assert archive_path.exists()
    assert zipfile.is_zipfile(archive_path)

    with zipfile.ZipFile(archive_path, "r") as zf:
        assert zf.testzip() is None
        zf.extractall(restore_dir)

    extracted_root = restore_dir / source_dir.name
    assert (extracted_root / "Preferences").exists()
    assert (extracted_root / "Cookies").exists()
    assert (
        extracted_root
        / "IndexedDB"
        / "https_example_0.indexeddb.leveldb"
        / "empty_marker.dat"
    ).stat().st_size == 0


def test_unmocked_compress_disambiguates_duplicate_source_names(
    roundtrip_env: Tuple[Path, Path, Path, Dict[str, str]],
) -> None:
    """Verify duplicate source directory names receive safe suffixes."""
    source_dir, dest_dir, restore_dir, _ = roundtrip_env
    second_dir = source_dir.parent / "other_parent" / source_dir.name
    second_dir.mkdir(parents=True, exist_ok=True)
    (second_dir / "other.txt").write_text("second copy", encoding="utf-8")

    zip_path = archive.compress(
        [source_dir, second_dir], zip_name="multi.zip"
    )
    assert zip_path is not None and zip_path.exists()

    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(restore_dir)

    assert (restore_dir / source_dir.name).is_dir()
    assert (restore_dir / f"{source_dir.name}(1)").is_dir()
    assert (
        restore_dir / f"{source_dir.name}(1)" / "other.txt"
    ).read_text(encoding="utf-8") == "second copy"
