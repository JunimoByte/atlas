"""Atlas | Archive | Attribute Management.

Handles file metadata, timestamps, and permissions for ZIP archives.
"""

# =============================================================================
# IMPORTS
# =============================================================================

import logging
import os
import sys
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

# =============================================================================
# LOGGING
# =============================================================================

LOGGER = logging.getLogger(__name__)

# =============================================================================
# FUNCTIONS
# =============================================================================


def safe_zipinfo_date(file_path: Path) -> Tuple[int, int, int, int, int, int]:
    """Return a safe datetime tuple for ZIP (year >= 1980).

    Args:
        file_path (Path): Path to the file.

    Returns:
        Tuple[int, int, int, int, int, int]: Date tuple (Y, M, D, h, m, s).

    """
    try:
        mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
        year = max(1980, min(mtime.year, 2107))
        return (
            year,
            mtime.month,
            mtime.day,
            mtime.hour,
            mtime.minute,
            mtime.second,
        )
    except Exception as error:
        LOGGER.debug(
            "Failed to get file date for {}: {}".format(file_path, error)
        )
        return 1980, 1, 1, 0, 0, 0


def get_windows_version() -> Optional[Tuple[int, int]]:
    """Retrieve the major and minor Windows version.

    Returns:
        Optional[Tuple[int, int]]: The (major, minor) version tuple,
        or None if not Windows or detection fails.

    """
    if os.name != "nt":
        return None

    try:
        ver_info = sys.getwindowsversion()
        return int(ver_info.major), int(ver_info.minor)
    except Exception as error:
        LOGGER.debug(
            "Failed to get Windows version: {}".format(error)
        )
        return None


def set_file_permissions(st_mode: int) -> int:
    """Return external_attr for ZIP based on OS and Windows version.

    Args:
        st_mode (int): The file mode from os.stat.

    Returns:
        int: The external attribute integer for ZipInfo.

    """
    windows_ver = get_windows_version()
    if windows_ver:
        major, minor = windows_ver
        if major < 6 or (major == 6 and minor <= 1):
            return 0o600 << 16
    return st_mode << 16


def create_zip_info(file_path: Path) -> zipfile.ZipInfo:
    """Create a ZipInfo object with metadata from the file.

    Args:
        file_path (Path): File to create ZipInfo for.

    Returns:
        zipfile.ZipInfo: Configured ZipInfo object.

    """
    zi = zipfile.ZipInfo()
    try:
        st = file_path.stat()
        zi.date_time = safe_zipinfo_date(file_path)
        zi.external_attr = set_file_permissions(st.st_mode)
    except Exception as error:
        LOGGER.debug(
            "Failed to set file attributes for {}: {}".format(file_path, error)
        )
        zi.external_attr = 0o600 << 16
    return zi
