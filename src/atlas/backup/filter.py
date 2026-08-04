"""Atlas | Archive | Filter Management.

Handles file filtering, blacklist logic, and file validation for backups.
"""

# =============================================================================
# IMPORTS
# =============================================================================

import logging
import os
from pathlib import Path
from typing import Callable, Generator, List, Optional, Tuple

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


def scan_files(  # noqa: C901
    source_paths: List[Path],
    cancel_callback: Optional[Callable[[], bool]] = None,
) -> Generator[Tuple[Path, Path], None, None]:
    """Walk directories and yield (source_root, file_path) pairs to compress.

    Skip blacklisted folders, blacklisted file extensions, symlinks,
    unreadable files, huge files, and Windows alternate data streams.

    Yielding the source root alongside the file path avoids downstream
    callers needing to re-resolve which source directory a file belongs to.

    Args:
        source_paths (List[Path]): List of directory paths to scan.
        cancel_callback (Optional[Callable[[], bool]]): Function to
            check for cancellation.

    Yields:
        Tuple[Path, Path]: (source_root, file_path) pairs.

    """
    for source_path in source_paths:
        root_path = Path(source_path)

        if not root_path.exists() or not root_path.is_dir():
            continue

        stack = [str(root_path)]

        while stack:
            if cancel_callback and cancel_callback():
                return

            current_dir = stack.pop()

            try:
                with os.scandir(current_dir) as entries:
                    for entry in entries:
                        if cancel_callback and cancel_callback():
                            return

                        try:
                            if entry.is_dir(follow_symlinks=False):
                                if entry.name not in SKIP_FOLDERS:
                                    stack.append(entry.path)
                            elif entry.is_file(follow_symlinks=False):
                                file_name = entry.name
                                file_ext = Path(file_name).suffix

                                if file_ext in SKIP_FILE_EXTENSION:
                                    continue

                                if (
                                    file_ext in SKIP_FILE_WITH_EXTENSION
                                    and file_name
                                    in SKIP_FILE_WITH_EXTENSION[file_ext]
                                ):
                                    continue

                                if os.name == "nt" and ":" in file_name:
                                    continue

                                stat_info = entry.stat(follow_symlinks=False)

                                if stat_info.st_size > MAX_FILE_SIZE:
                                    continue

                                yield root_path, Path(current_dir) / file_name
                        except OSError as error:
                            LOGGER.debug(
                                "Scandir entry error for %s: %s",
                                getattr(entry, "path", "<unknown>"),
                                error,
                            )
                            continue
            except OSError as error:
                LOGGER.debug("Scandir error for %s: %s", current_dir, error)
                continue
