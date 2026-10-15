"""Atlas | Size Management.

File size formatting and disk space checking utilities for Atlas.
Provides human-readable size formatting and disk space validation.
"""

# =============================================================================
# IMPORTS
# =============================================================================

import errno
import logging
import math
import os
import shutil
import stat
import time
from pathlib import Path
from typing import Tuple, Union

from atlas.backup.archive import get_zip_output_dir
from atlas.lib.read import load_json
from atlas.lib.system import is_junction

# =============================================================================
# LOGGING
# =============================================================================

LOGGER = logging.getLogger(__name__)

# =============================================================================
# JSONS
# =============================================================================

try:
    BLACKLIST_JSON = load_json("blacklist.json")
    SKIP_FOLDERS = {f.lower() for f in BLACKLIST_JSON.get("SKIP_FOLDERS", [])}
except Exception as error:
    LOGGER.error("Failed to load blacklist.json: {}".format(error))
    raise RuntimeError(
        "Failed to load required blacklist configuration"
    ) from error

# =============================================================================
# CONSTANTS
# =============================================================================

MAX_SCAN_TIME = 300
SIZE_UNITS = ("B", "KB", "MB", "GB", "TB", "PB")
BYTES_PER_KIB = 1024
DISK_SPACE_SAFETY_FACTOR = 1.5

# =============================================================================
# EXCEPTIONS
# =============================================================================


class ScanTimeoutError(RuntimeError):
    """Raised when a directory size scan exceeds MAX_SCAN_TIME.

    The size returned would be partial and unsafe to use for
    disk-space decisions so callers should treat this conservatively.
    """


class ScanError(RuntimeError):
    """Raised when a directory scan encounters inaccessible files or folders.

    Like timeouts, incomplete scans mean the size estimate is unreliable
    and should not be trusted for disk-space approval.
    """


class _ScanCancelledError(InterruptedError):
    """Raised internally when a size scan observes cancellation."""


# =============================================================================
# FUNCTIONS
# =============================================================================


def _check_scan_interruption(
    start_time: float,
    path_str: Union[str, Path],
    cancel_callback: Union[None, callable],
) -> None:
    """Raise when a size scan has been cancelled or timed out."""
    if cancel_callback and cancel_callback():
        raise _ScanCancelledError("Directory size scan cancelled by user")

    if time.monotonic() - start_time > MAX_SCAN_TIME:
        raise ScanTimeoutError(
            "Directory scan timed out after {}s: {}".format(
                MAX_SCAN_TIME, path_str
            )
        )


def _get_scan_root(path_str: Union[str, Path]) -> Union[Path, None]:
    """Resolve an existing directory root without hiding I/O failures."""
    source = Path(path_str)
    try:
        root = source.resolve()
    except (OSError, RuntimeError) as error:
        LOGGER.debug("Could not resolve scan root %s: %s", source, error)
        try:
            root = source.absolute()
        except OSError as absolute_error:
            raise ScanError(
                "Could not resolve directory scan root: {}".format(path_str)
            ) from absolute_error

    try:
        root_stat = root.stat()
    except OSError as error:
        if error.errno in (errno.ENOENT, errno.ENOTDIR):
            return None
        raise ScanError(
            "Could not inspect directory scan root {}: {}".format(
                path_str, error
            )
        ) from error

    if not stat.S_ISDIR(root_stat.st_mode):
        return None
    return root


def format_size(bytes_size: Union[int, float]) -> str:
    """Format a byte size into a human-readable string.

    Args:
        bytes_size (Union[int, float]): Size in bytes.

    Returns:
        str: Formatted string (e.g., "1.5 MB").

    """
    try:
        bytes_size = float(bytes_size)
        if bytes_size < 0 or math.isnan(bytes_size) or math.isinf(bytes_size):
            return "Invalid size"

        for i, unit in enumerate(SIZE_UNITS):
            if bytes_size < BYTES_PER_KIB or i == len(SIZE_UNITS) - 1:
                if bytes_size.is_integer():
                    return "{} {}".format(int(bytes_size), unit)
                return "{:.2f}".format(bytes_size).rstrip("0").rstrip(
                    "."
                ) + " {}".format(unit)
            bytes_size /= BYTES_PER_KIB
    except (ValueError, TypeError):
        return "Unknown size"
    return "Unknown size"


def get_directory_size(  # noqa: C901
    path_str: Union[str, Path],
    cancel_callback: Union[None, callable] = None,
) -> int:
    """Recursively compute the total size of a directory.

    Uses ``os.scandir`` with a manual stack for performance. On Windows,
    ``DirEntry.stat()`` reuses the result from ``FindNextFile``, avoiding
    extra syscalls. Symlink check is folded into
    ``is_file(follow_symlinks=False)``.

    Args:
        path_str (Union[str, Path]): Path to the directory.
        cancel_callback (Optional[callable]): Callback to check for
            cancellation.

    Returns:
        int: Total size in bytes.

    """
    total = 0
    start_time = time.monotonic()
    scan_incomplete = False

    _check_scan_interruption(start_time, path_str, cancel_callback)
    root = _get_scan_root(path_str)
    _check_scan_interruption(start_time, path_str, cancel_callback)
    if root is None:
        return 0

    stack = [str(root)]

    while stack:
        _check_scan_interruption(start_time, path_str, cancel_callback)
        current_dir = stack.pop()

        try:
            with os.scandir(current_dir) as entries:
                for entry in entries:
                    _check_scan_interruption(
                        start_time, path_str, cancel_callback
                    )
                    try:
                        if entry.is_dir(follow_symlinks=False):
                            if is_junction(entry):
                                LOGGER.debug(
                                    "Skipping junction in size scan: %s",
                                    entry.path,
                                )
                                continue
                            if entry.name.lower() not in SKIP_FOLDERS:
                                stack.append(entry.path)
                        elif entry.is_file(follow_symlinks=False):
                            total += entry.stat(follow_symlinks=False).st_size
                    except OSError as error:
                        LOGGER.debug(
                            "Error accessing %s: %s", entry.path, error
                        )
                        scan_incomplete = True
                    finally:
                        _check_scan_interruption(
                            start_time, path_str, cancel_callback
                        )
        except _ScanCancelledError:
            raise
        except OSError as error:
            LOGGER.debug("Cannot scan directory %s: %s", current_dir, error)
            scan_incomplete = True

        _check_scan_interruption(start_time, path_str, cancel_callback)

    if scan_incomplete:
        raise ScanError(
            "Directory scan was incomplete due to inaccessible "
            "paths: {}".format(path_str)
        )

    return total


def check_disk_space(
    estimated_size_bytes: int, output_path: Union[str, Path, None] = None
) -> Tuple[bool, str]:
    """Check if there's sufficient disk space for the backup.

    Args:
        estimated_size_bytes (int): Estimated backup size in bytes.
        output_path (Union[str, Path, None]): Optional custom output path.

    Returns:
        Tuple[bool, str]: (True if sufficient space,
            Formatted available space).

    """
    if estimated_size_bytes < 0:
        LOGGER.warning(
            "check_disk_space called with negative size: %d",
            estimated_size_bytes,
        )
        return False, "Unknown"

    try:
        output_dir = (
            Path(output_path).resolve()
            if output_path
            else get_zip_output_dir()
        )
        output_dir.mkdir(parents=True, exist_ok=True)
        _, _, free = shutil.disk_usage(output_dir)

        required_space = int(
            estimated_size_bytes * DISK_SPACE_SAFETY_FACTOR
        )
        has_sufficient_space = free >= required_space

        return has_sufficient_space, format_size(free)

    except OSError as error:
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
        Path(output_path).resolve() if output_path else get_zip_output_dir()
    )
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        LOGGER.info("Output directory ready: %s", output_dir)
    except OSError as error:
        LOGGER.error("Failed to create output directory: %s", error)
        raise
    return output_dir
