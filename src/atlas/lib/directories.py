"""Atlas | Packages | Directories.

Cross-platform user directory resolution for Atlas.

Provides safe, validated access to well-known user directories
such as the Downloads folder across Windows, macOS, and Linux.
"""

# =============================================================================
# IMPORTS
# =============================================================================

import ctypes
import logging
import os
import platform
import re
import sys
from pathlib import Path
from typing import Optional

# =============================================================================
# LOGGING
# =============================================================================

LOGGER = logging.getLogger(__name__)

# =============================================================================
# CONSTANTS
# =============================================================================

_DOWNLOADS_SUBDIR = "Downloads"

# =============================================================================
# FUNCTIONS
# =============================================================================


def get_downloads_dir() -> Path:
    """Return the path to the current user's Downloads directory.

    Resolve the Downloads folder using platform-specific methods
    with progressively broader fallbacks so that the result is
    reliable even on minimal installations (e.g. Arch Linux
    without ``xdg-user-dirs``).

    On Windows the resolution order is:

    1. ``SHGetKnownFolderPath`` (Vista+).
    2. ``HKCU\\...\\User Shell Folders`` registry key (XP+).
    3. ``%USERPROFILE%\\Downloads``.
    4. Directory adjacent to the running executable.

    On macOS the path is ``~/Downloads``.

    On Linux and BSD the function reads the XDG ``user-dirs.dirs``
    config file first, then the ``XDG_DOWNLOAD_DIR`` environment
    variable, then falls back to ``~/Downloads``, and finally to
    the exe-adjacent directory.

    The directory is created (with parents) if it does not
    already exist.  If creation fails on every candidate, the
    exe-adjacent directory is used as a guaranteed last resort.

    Returns:
        Path: Absolute path to the Downloads directory.

    """
    system = platform.system().lower()

    if system == "windows":
        candidates = _get_windows_candidates()
    elif system == "darwin":
        candidates = [_get_downloads_posix_fallback()]
    else:
        candidates = _get_linux_candidates()

    # Walk candidates until one can be created/used.
    for candidate in candidates:
        resolved = candidate.resolve()
        if _ensure_directory(resolved):
            LOGGER.info(
                "Resolved Downloads directory: %s", resolved
            )
            return resolved

    # Guaranteed last resort: directory next to the executable.
    fallback = _get_exe_adjacent_dir()
    resolved = fallback.resolve()
    _ensure_directory(resolved)
    LOGGER.warning(
        "All standard download locations failed; "
        "using exe-adjacent directory: %s",
        resolved,
    )
    return resolved


# =============================================================================
# WINDOWS RESOLUTION
# =============================================================================


def _get_windows_candidates() -> list:
    """Return ordered list of Windows download dir candidates.

    Returns:
        list: List of Path candidates, most preferred first.

    """
    candidates = []

    path = _shell_known_folder_path()
    if path is not None:
        candidates.append(path)

    path = _shell_folder_path_registry()
    if path is not None:
        candidates.append(path)

    candidates.append(_get_downloads_posix_fallback())
    return candidates


def _shell_known_folder_path() -> Optional[Path]:
    """Call SHGetKnownFolderPath for FOLDERID_Downloads (Vista+).

    Returns:
        Optional[Path]: The Downloads path, or None on failure.

    """
    try:
        from ctypes import wintypes

        # FOLDERID_Downloads GUID
        # {374DE290-123F-4565-9164-39C4925E467B}
        class _GUID(ctypes.Structure):
            """COM GUID / UUID structure."""

            _fields_ = [
                ("Data1", wintypes.DWORD),
                ("Data2", wintypes.WORD),
                ("Data3", wintypes.WORD),
                ("Data4", wintypes.BYTE * 8),
            ]

        folderid_downloads = _GUID()
        folderid_downloads.Data1 = 0x374DE290
        folderid_downloads.Data2 = 0x123F
        folderid_downloads.Data3 = 0x4565
        folderid_downloads.Data4[:] = (
            0x91, 0x64, 0x39, 0xC4,
            0x92, 0x5E, 0x46, 0x7B,
        )

        shell32 = ctypes.windll.shell32
        ole32 = ctypes.windll.ole32

        path_ptr = ctypes.c_wchar_p()
        result = shell32.SHGetKnownFolderPath(
            ctypes.byref(folderid_downloads),
            0,
            None,
            ctypes.byref(path_ptr),
        )

        if result != 0:
            LOGGER.debug(
                "SHGetKnownFolderPath returned HRESULT 0x%08X",
                result,
            )
            return None

        folder = Path(path_ptr.value)
        ole32.CoTaskMemFree(path_ptr)
        return folder

    except Exception as error:
        LOGGER.debug(
            "SHGetKnownFolderPath failed: %s", error
        )
        return None


def _shell_folder_path_registry() -> Optional[Path]:
    """Read the Downloads path from the Windows registry (XP+).

    Queries ``HKCU\\...\\User Shell Folders`` for the Downloads
    GUID ``{374DE290-123F-4565-9164-39C4925E467B}``.  Windows XP
    does not have a Downloads shell folder by default, but this
    key will contain it if Internet Explorer or the user has
    configured one.  On Vista and later the key is always
    present alongside ``SHGetKnownFolderPath``.

    Environment-variable strings such as ``%USERPROFILE%`` are
    expanded before the path is returned.

    Returns:
        Optional[Path]: The Downloads path, or None on failure.

    """
    try:
        import winreg

        guid = "{374DE290-123F-4565-9164-39C4925E467B}"
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion"
            r"\Explorer\User Shell Folders",
        ) as key:
            raw, _ = winreg.QueryValueEx(key, guid)

        expanded = os.path.expandvars(raw)
        path = Path(expanded)

        if not path.is_absolute():
            LOGGER.debug(
                "Registry Downloads path is relative, "
                "ignoring: %s",
                path,
            )
            return None

        LOGGER.debug(
            "Resolved Downloads from registry: %s", path
        )
        return path

    except Exception as error:
        LOGGER.debug(
            "Registry Downloads lookup failed: %s", error
        )
        return None


# =============================================================================
# LINUX / BSD RESOLUTION
# =============================================================================


def _get_linux_candidates() -> list:
    """Return ordered list of Linux/BSD download dir candidates.

    Returns:
        list: List of Path candidates, most preferred first.

    """
    candidates = []

    path = _parse_xdg_user_dirs_file()
    if path is not None:
        candidates.append(path)

    path = _read_xdg_env_var()
    if path is not None:
        candidates.append(path)

    candidates.append(_get_downloads_posix_fallback())
    return candidates


def _parse_xdg_user_dirs_file() -> Optional[Path]:
    """Read XDG_DOWNLOAD_DIR from ``user-dirs.dirs``.

    The file is typically located at
    ``$XDG_CONFIG_HOME/user-dirs.dirs`` or, when that variable
    is unset, ``~/.config/user-dirs.dirs``.  Lines have the
    format ``XDG_DOWNLOAD_DIR="$HOME/Downloads"``.

    Returns:
        Optional[Path]: Parsed path, or None if unavailable.

    """
    config_home = os.environ.get(
        "XDG_CONFIG_HOME",
        os.path.join(Path.home(), ".config"),
    )
    dirs_file = Path(config_home) / "user-dirs.dirs"

    if not dirs_file.is_file():
        LOGGER.debug(
            "user-dirs.dirs not found at %s", dirs_file
        )
        return None

    try:
        content = dirs_file.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        LOGGER.debug(
            "Could not read %s: %s", dirs_file, error
        )
        return None

    pattern = re.compile(
        r'^XDG_DOWNLOAD_DIR\s*=\s*"(.+)"', re.MULTILINE
    )
    match = pattern.search(content)
    if match is None:
        LOGGER.debug(
            "XDG_DOWNLOAD_DIR not found in %s", dirs_file
        )
        return None

    raw_value = match.group(1)
    expanded = raw_value.replace("$HOME", str(Path.home()))
    resolved = Path(expanded).expanduser()

    if not resolved.is_absolute():
        LOGGER.debug(
            "Ignoring relative XDG_DOWNLOAD_DIR: %s",
            resolved,
        )
        return None

    LOGGER.debug(
        "Resolved XDG_DOWNLOAD_DIR from user-dirs.dirs: %s",
        resolved,
    )
    return resolved


def _read_xdg_env_var() -> Optional[Path]:
    """Read the ``XDG_DOWNLOAD_DIR`` environment variable.

    Returns:
        Optional[Path]: The path if the variable is set and
            absolute, otherwise None.

    """
    value = os.environ.get("XDG_DOWNLOAD_DIR")
    if not value:
        return None

    path = Path(value).expanduser()
    if not path.is_absolute():
        LOGGER.debug(
            "Ignoring relative XDG_DOWNLOAD_DIR env: %s",
            path,
        )
        return None

    LOGGER.debug(
        "Resolved XDG_DOWNLOAD_DIR from environment: %s",
        path,
    )
    return path


# =============================================================================
# SHARED HELPERS
# =============================================================================


def _get_downloads_posix_fallback() -> Path:
    """Return ``~/Downloads`` as a near-universal fallback.

    Returns:
        Path: ``~/Downloads`` expanded to an absolute path.

    """
    return Path.home() / _DOWNLOADS_SUBDIR


def _get_exe_adjacent_dir() -> Path:
    """Return a directory next to the running executable.

    When frozen by PyInstaller ``sys.executable`` points to the
    ``.exe``.  In development it points to the Python interpreter,
    so the parent of ``__file__`` is used instead to place output
    next to the source entry point.

    Returns:
        Path: Absolute path to the ``output`` directory adjacent
            to the executable (or source root in dev mode).

    """
    if getattr(sys, "frozen", False):
        base = Path(sys.executable).parent
    else:
        base = Path(__file__).parent.parent.parent

    return base / "output"


def _ensure_directory(path: Path) -> bool:
    """Create a directory (and parents) if it does not exist.

    Args:
        path: Directory to create.

    Returns:
        bool: True if the directory exists or was created
            successfully, False otherwise.

    """
    try:
        path.mkdir(parents=True, exist_ok=True)
        return True
    except OSError as error:
        LOGGER.warning(
            "Could not create directory %s: %s",
            path,
            error,
        )
        return False
