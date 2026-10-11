"""Atlas | Tests | Backup | Locked Files.

Resilience tests for in-use, locked, or unreadable browser profile files.
Validates that locked files are safely skipped, warnings are logged,
and clean archives are produced without leaving dangling temporary files.
"""

# =============================================================================
# IMPORTS
# =============================================================================

import os
import platform
import zipfile
from pathlib import Path
from typing import Generator, Tuple
from unittest.mock import patch

import pytest

from atlas.backup import archive

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def locked_env(tmp_path: Path) -> Generator[Tuple[Path, Path], None, None]:
    """Provide isolated source and output directories."""
    source_dir = tmp_path / "locked_profile"
    source_dir.mkdir(parents=True, exist_ok=True)
    dest_dir = tmp_path / "locked_output"
    dest_dir.mkdir(parents=True, exist_ok=True)

    archive.set_zip_output_dir(dest_dir)
    try:
        yield source_dir, dest_dir
    finally:
        archive.set_zip_output_dir(None)


# =============================================================================
# TESTS — File Lock & Access Denied Resilience
# =============================================================================


def test_locked_file_skipped_and_healthy_files_preserved(
    locked_env: Tuple[Path, Path],
) -> None:
    """Verify in-use file is skipped while other files are safely archived."""
    source_dir, dest_dir = locked_env

    file1 = source_dir / "healthy1.txt"
    file1.write_text("healthy one", encoding="utf-8")
    locked_file = source_dir / "LOCK"
    locked_file.write_text("in-use lock payload", encoding="utf-8")
    file2 = source_dir / "healthy2.txt"
    file2.write_text("healthy two", encoding="utf-8")

    import io

    real_io_open = io.open

    def selective_open(file, *args, **kwargs):
        if "LOCK" in str(file):
            raise PermissionError(13, "Permission denied (in use)")
        return real_io_open(file, *args, **kwargs)

    with patch("io.open", side_effect=selective_open):
        zip_path = archive.compress([source_dir], zip_name="partial_lock.zip")

    assert zip_path is not None
    assert zip_path.is_file()
    assert not zip_path.with_suffix(".zip.tmp").exists()

    with zipfile.ZipFile(zip_path, "r") as zf:
        assert zf.testzip() is None
        names = {info.filename.split("/")[-1] for info in zf.infolist()}
        assert "healthy1.txt" in names
        assert "healthy2.txt" in names
        assert "LOCK" not in names


def test_all_files_locked_aborts_without_orphan_temp_archive(
    locked_env: Tuple[Path, Path],
) -> None:
    """Verify total lock failure produces no dangling temporary files."""
    source_dir, dest_dir = locked_env

    (source_dir / "file1.dat").write_text("data 1", encoding="utf-8")
    (source_dir / "file2.dat").write_text("data 2", encoding="utf-8")

    import io

    real_io_open = io.open

    def deny_all(file, *args, **kwargs):
        # Allow archive zip writing to proceed so write_zip creates temp zip
        if "all_locked" in str(file):
            return real_io_open(file, *args, **kwargs)
        raise PermissionError("Access denied on all files")

    with patch("io.open", side_effect=deny_all):
        result = archive.compress([source_dir], zip_name="all_locked.zip")

    assert result is None
    # Verify no orphan archives or temporary files remain
    assert not (dest_dir / "all_locked.zip").exists()
    assert not (dest_dir / "all_locked.zip.tmp").exists()


def test_native_os_lock_skipped_gracefully(
    locked_env: Tuple[Path, Path],
) -> None:
    """Verify native operating system locks are handled gracefully."""
    source_dir, dest_dir = locked_env

    healthy = source_dir / "healthy.txt"
    healthy.write_text("healthy content", encoding="utf-8")
    locked_target = source_dir / "active.lock"
    locked_target.write_text("locked content", encoding="utf-8")

    system_name = platform.system()

    if system_name == "Windows":
        import msvcrt

        # Acquire an exclusive file lock on Windows
        with locked_target.open("r+b") as handle:
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            try:
                zip_path = archive.compress(
                    [source_dir], zip_name="native_win_lock.zip"
                )
            finally:
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        # On POSIX systems, remove read permissions
        try:
            os.chmod(str(locked_target), 0o000)
            zip_path = archive.compress(
                [source_dir], zip_name="native_posix_lock.zip"
            )
        finally:
            os.chmod(str(locked_target), 0o644)

    assert zip_path is not None
    assert zip_path.is_file()

    with zipfile.ZipFile(zip_path, "r") as zf:
        assert zf.testzip() is None
        names = {info.filename.split("/")[-1] for info in zf.infolist()}
        assert "healthy.txt" in names
