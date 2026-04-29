"""Atlas | Packages | Integration.

User-facing operating system integration helpers for Atlas.

Provides safe, cross-platform access to desktop features such as
opening folders in the system file manager.
"""

# =============================================================================
# IMPORTS
# =============================================================================

import logging
import os
import platform
import subprocess
from pathlib import Path
from typing import Optional

from atlas.backup import archive as Archive
from atlas.display.popup import show_warning

# =============================================================================
# LOGGING
# =============================================================================

LOGGER = logging.getLogger(__name__)

# =============================================================================
# FUNCTIONS
# =============================================================================


def open_folder(folder_path: Optional[Path] = None) -> None:
    """Resolve and open the selected folder in the file manager.

    If no folder is provided, attempt to open the archive output
    directory.  Display a user-facing warning if the folder does
    not exist or cannot be opened automatically.

    Args:
        folder_path (Optional[Path]): Specific path to open.
            Defaults to None.

    """
    try:
        if folder_path is None:
            folder_path = Archive.get_zip_output_dir()

        if folder_path is None:
            LOGGER.warning("No folder path available to open")
            show_warning(
                title="Caution",
                message="Folder Not Found",
                details=(
                    "The selected folder could not be "
                    "found.\n\n"
                    "It may have been moved or deleted."
                ),
            )
            return

        folder = folder_path.resolve()

        if not folder.exists():
            LOGGER.warning(
                "Selected folder missing: %s", folder
            )
            show_warning(
                title="Caution",
                message="Folder Not Found",
                details=(
                    "The selected folder could not be "
                    "found.\n\n"
                    "It may have been moved or deleted."
                ),
            )
            return

        _open_folder_platform(folder)
        LOGGER.info("Opened folder: %s", folder)

    except FileNotFoundError as error:
        LOGGER.warning(
            "Failed to open folder: %s",
            error,
            exc_info=True,
        )
        show_warning(
            title="Caution",
            message="Failed to Open Folder",
            details=(
                "Atlas could not open the selected folder "
                "automatically.\n\n"
                "Please open it manually using your file "
                "manager."
            ),
        )

    except Exception as error:
        LOGGER.warning(
            "Failed to open folder: %s",
            error,
            exc_info=True,
        )
        show_warning(
            title="Caution",
            message="Failed to Open Folder",
            details=(
                "Atlas ran into an error while trying to "
                "open the selected folder.\n\n"
                "Please try again later."
            ),
        )


def _open_folder_platform(folder_path: Path) -> None:
    """Open a folder using the system file manager."""
    system = platform.system().lower()

    if system == "windows":
        os.startfile(folder_path)
    elif system == "darwin":
        subprocess.call(["open", str(folder_path)])
    else:
        env = os.environ.copy()
        env.pop("LD_LIBRARY_PATH", None)
        subprocess.Popen(
            ["xdg-open", str(folder_path)],
            env=env,
            start_new_session=True,
            close_fds=True,
        )
