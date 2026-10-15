"""Atlas | Packages | System.

Centralized system identification and OS string normalization.
"""

import os
import platform


def normalize_os_key(os_name: str) -> str:
    """Normalize a raw OS string into a stable configuration key.

    Maps BSD variants to 'BSD' and Darwin to 'Macos'.

    Args:
        os_name: Raw OS string (e.g., from platform.system()).

    Returns:
        str: Normalized OS key (e.g. 'Windows', 'Linux', 'Macos', 'BSD').

    """
    sys_name = os_name.strip().lower()

    if (
        sys_name == "bsd"
        or sys_name.endswith("bsd")
        or sys_name == "dragonfly"
    ):
        return "BSD"

    if sys_name in ("sunos", "solaris", "illumos"):
        return "SOLARIS"

    if sys_name in ("darwin", "macos", "mac"):
        return "Macos"

    if sys_name in ("windows", "win32"):
        return "Windows"

    # Windows -> Windows, Linux -> Linux
    return sys_name.capitalize()


def get_os_key() -> str:
    """Return the normalized, capitalized OS name for the current system."""
    return normalize_os_key(platform.system())


def is_junction(path_or_entry: object) -> bool:
    """Return True if path or DirEntry is a Windows directory junction.

    Args:
        path_or_entry: A path string, Path object, or os.DirEntry.

    Returns:
        bool: True if target is an NTFS directory junction or reparse point.
    """
    if os.name != "nt":
        return False

    is_junc = getattr(os.path, "isjunction", None)
    if is_junc is not None:
        try:
            return bool(is_junc(path_or_entry))
        except (OSError, ValueError):
            return False

    try:
        if hasattr(path_or_entry, "stat"):
            st = path_or_entry.stat(follow_symlinks=False)
        else:
            st = os.lstat(str(path_or_entry))
        tag = getattr(st, "st_reparse_tag", 0)
        attrs = getattr(st, "st_file_attributes", 0)
        return bool(tag == 0xA0000003 or (attrs & 0x400))
    except (OSError, ValueError):
        return False
