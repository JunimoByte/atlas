"""Atlas | Archive | Filter Management.

Handles file filtering, blacklist logic, and file validation for backups.
"""

# =============================================================================
# IMPORTS
# =============================================================================

import logging
import os
from pathlib import Path
from typing import Callable, List, Optional

from atlas.lib.read import load_json

# =============================================================================
# LOGGING
# =============================================================================

LOGGER = logging.getLogger(__name__)

# =============================================================================
# BLACKLIST CONFIGURATION
# =============================================================================

try:
    BLACKLIST_JSON = load_json("blacklist.json")
    SKIP_FOLDERS = set(BLACKLIST_JSON.get("SKIP_FOLDERS", []))
    SKIP_FILE_EXTENSION = set(BLACKLIST_JSON.get("SKIP_FILE_EXTENSION", []))
    SKIP_FILE_WITH_EXTENSION = {
        ext: set(names)
        for ext, names in BLACKLIST_JSON.get(
            "SKIP_FILE_WITH_EXTENSION", {}
        ).items()
    }
except Exception as error:
    LOGGER.warning("Failed to load blacklist.json: {}".format(error))
    SKIP_FOLDERS = set()
    SKIP_FILE_EXTENSION = set()
    SKIP_FILE_WITH_EXTENSION = {}

# =============================================================================
# CONSTANTS
# =============================================================================

MAX_FILE_SIZE = 25 * 1024**3

# =============================================================================
# FUNCTIONS
# =============================================================================


def scan_files(
    source_paths: List[Path],
    cancel_callback: Optional[Callable[[], bool]] = None
) -> List[Path]:
    """Walk directories and return a list of valid files to compress.

    Skip blacklisted folders, blacklisted file extensions, symlinks,
    unreadable files, huge files, and Windows alternate data streams.

    Args:
        source_paths (List[Path]): List of directory paths to scan.
        cancel_callback (Optional[Callable[[], bool]]): Function to
            check for cancellation.

    Returns:
        List[Path]: List of valid file paths to include in the archive.

    """
    valid_files: List[Path] = []

    for source_path in source_paths:
        for root, dirs, files in os.walk(source_path):

            if cancel_callback and cancel_callback():
                return []

            dirs[:] = [d for d in dirs if d not in SKIP_FOLDERS]

            with os.scandir(root) as entries:
                for entry in entries:

                    if cancel_callback and cancel_callback():
                        return []

                    if not entry.is_file(follow_symlinks=False):
                        continue

                    file_name = entry.name
                    file_ext = Path(file_name).suffix

                    if file_ext in SKIP_FILE_EXTENSION:
                        continue

                    if (
                        file_ext in SKIP_FILE_WITH_EXTENSION
                        and file_name in SKIP_FILE_WITH_EXTENSION[file_ext]
                    ):
                        continue

                    if os.name == "nt" and ":" in file_name:
                        continue

                    try:
                        stat_info = entry.stat(follow_symlinks=False)
                    except OSError:
                        continue

                    if stat_info.st_size > MAX_FILE_SIZE:
                        continue

                    valid_files.append(Path(root) / file_name)

    return valid_files
