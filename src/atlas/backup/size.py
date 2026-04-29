"""Atlas | Size Management.

File size formatting and disk space checking utilities for Atlas.
Provides human-readable size formatting and disk space validation.
"""

# =============================================================================
# IMPORTS
# =============================================================================

import gc
import logging
import os
import shutil
import time
from pathlib import Path
from typing import Tuple, Union

from atlas.backup.archive import get_zip_output_dir
from atlas.lib.read import load_json

# =============================================================================
# LOGGING
# =============================================================================

LOGGER = logging.getLogger(__name__)

# =============================================================================
# JSONS
# =============================================================================

try:
    BLACKLIST_JSON = load_json("blacklist.json")
    SKIP_FOLDERS = set(BLACKLIST_JSON.get("SKIP_FOLDERS", []))
except Exception:
    LOGGER.warning("Failed to load blacklist.json", exc_info=True)
    SKIP_FOLDERS = set()

# =============================================================================
# CONSTANTS
# =============================================================================

CHUNK_SIZE = 1000
MAX_SCAN_TIME = 300

# =============================================================================
# EXCEPTIONS
# =============================================================================


class ScanTimeoutError(RuntimeError):
    """Raised when a directory size scan exceeds MAX_SCAN_TIME.

    The size returned would be partial and unsafe to use for
    disk-space decisions so callers should treat this conservatively.
    """


# =============================================================================
# FUNCTIONS
# =============================================================================


def format_size(bytes_size: Union[int, float]) -> str:
    """Format a byte size into a human-readable string.

    Args:
        bytes_size (Union[int, float]): Size in bytes.

    Returns:
        str: Formatted string (e.g., "1.5 MB").

    """
    try:
        bytes_size = float(bytes_size)
        if bytes_size < 0:
            return "Invalid size"

        units = ["B", "KB", "MB", "GB", "TB", "PB"]
        for i, unit in enumerate(units):
            if bytes_size < 1024 or i == len(units) - 1:
                if bytes_size.is_integer():
                    return "{} {}".format(int(bytes_size), unit)
                return (
                    "{:.2f}".format(bytes_size).rstrip("0").rstrip(".")
                    + " {}".format(unit)
                )
            bytes_size /= 1024
    except (ValueError, TypeError):
        return "Unknown size"
    return "Unknown size"


def get_directory_size(path_str: Union[str, Path]) -> int:
    """Recursively compute the total size of a directory.

    Uses ``os.scandir`` with a manual stack for performance. On Windows,
    ``DirEntry.stat()`` reuses the result from ``FindNextFile``, avoiding
    extra syscalls. Symlink check is folded into ``is_file(follow_symlinks=False)``.

    Args:
        path_str (Union[str, Path]): Path to the directory.

    Returns:
        int: Total size in bytes.

    """
    total = 0
    file_count = 0
    start_time = time.time()
    try:
        root = Path(path_str).resolve()
    except (FileNotFoundError, OSError):
        root = Path(path_str).absolute()

    if not root.exists() or not root.is_dir():
        return 0

    stack = [str(root)]

    while stack:
        current_dir = stack.pop()

        if time.time() - start_time > MAX_SCAN_TIME:
            raise ScanTimeoutError(
                "Directory scan timed out after {}s: {}".format(
                    MAX_SCAN_TIME, path_str
                )
            )

        try:
            with os.scandir(current_dir) as entries:
                for entry in entries:
                    try:
                        if entry.is_dir(follow_symlinks=False):
                            if entry.name not in SKIP_FOLDERS:
                                stack.append(entry.path)
                        elif entry.is_file(follow_symlinks=False):
                            total += entry.stat(follow_symlinks=False).st_size
                            file_count += 1
                            if file_count % CHUNK_SIZE == 0:
                                gc.collect()
                    except (PermissionError, FileNotFoundError, OSError) as error:
                        LOGGER.debug(
                            "Error accessing %s: %s", entry.path, error
                        )
        except (PermissionError, OSError) as error:
            LOGGER.debug("Cannot scan directory %s: %s", current_dir, error)

    gc.collect()
    return total


def check_disk_space(
    estimated_size_bytes: int,
    output_path: Union[str, Path, None] = None
) -> Tuple[bool, str]:
    """Check if there's sufficient disk space for the backup.

    Args:
        estimated_size_bytes (int): Estimated backup size in bytes.
        output_path (Union[str, Path, None]): Optional custom output path.

    Returns:
        Tuple[bool, str]: (True if sufficient space,
            Formatted available space).

    """
    try:
        output_dir = (
            Path(output_path).resolve()
            if output_path
            else get_zip_output_dir()
        )
        output_dir.mkdir(parents=True, exist_ok=True)
        _, _, free = shutil.disk_usage(output_dir)

        required_space = int(estimated_size_bytes * 1.5)
        has_sufficient_space = free >= required_space

        return has_sufficient_space, format_size(free)

    except Exception as error:
        LOGGER.error("Error checking disk space: {}".format(error))
        return False, "Unknown"


def create_output_dir(output_path: Union[str, Path, None] = None) -> Path:
    """Create the output directory after disk space check.

    Args:
        output_path (Union[str, Path, None]): Optional custom output path.

    Returns:
        Path: Path to the created output directory.

    """
    output_dir = (
        Path(output_path).resolve()
        if output_path
        else get_zip_output_dir()
    )
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        LOGGER.info("Output directory ready: %s", output_dir)
    except Exception as error:
        LOGGER.error("Failed to create output directory: %s", error)
        raise
    return output_dir
