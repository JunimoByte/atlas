"""Atlas | Archive | Filesystem Utilities.

Filesystem helpers for archive operations.
"""

# =============================================================================
# IMPORTS
# =============================================================================

import logging
import os
from pathlib import Path
from typing import List, Optional

# =============================================================================
# LOGGING
# =============================================================================

LOGGER = logging.getLogger(__name__)

# =============================================================================
# FUNCTIONS
# =============================================================================


def safe_unlink(path: Path) -> None:
    """Safely delete a file, suppressing errors.

    Args:
        path (Path): Path to the file to delete.

    """
    try:
        if path.exists():
            path.unlink()
    except Exception as error:
        LOGGER.warning("Failed to delete {}: {}".format(path, error))


def find_base_path(file_path: Path, sources: List[Path]) -> Optional[Path]:
    """Find which source directory contains the file.

    Args:
        file_path (Path): File to locate.
        sources (List[Path]): List of source directories.

    Returns:
        Optional[Path]: The base path if found, None otherwise.

    """
    for source in sources:
        if source in file_path.parents:
            return source
    return None


def relative_zip_path(file_path: Path, base_path: Path) -> str:
    """Return a relative path for ZIP entries, safe for NUL bytes.

    Args:
        file_path (Path): Path to the file.
        base_path (Path): Base directory path.

    Returns:
        str: Sanitized relative path string.

    """
    rel_path = "{}/{}".format(base_path.name, file_path.relative_to(base_path))
    rel_path = rel_path.replace(os.sep, "/")
    rel_path = rel_path.replace("\x00", "_")
    return rel_path
