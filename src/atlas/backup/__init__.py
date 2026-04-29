"""Atlas | Backup.

Browser profile backup and compression management.
"""

from .archive import ZIP_OUTPUT_DIR, compress, get_zip_output_dir
from .pipeline import Pipeline
from .profile import find_profile, get_browser_name_from_path
from .size import (
    check_disk_space,
    create_output_dir,
    format_size,
    get_directory_size,
)
from .worker import Worker

__all__ = [
    "Worker",
    "Pipeline",
    "find_profile",
    "get_browser_name_from_path",
    "format_size",
    "get_directory_size",
    "create_output_dir",
    "check_disk_space",
    "compress",
    "ZIP_OUTPUT_DIR",
    "get_zip_output_dir",
]
