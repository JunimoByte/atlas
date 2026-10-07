"""Atlas | Packages | Permissions.

Cross-platform permission validation for Atlas.

Prevents elevated execution (sudo/admin) for security reasons.
"""

# =============================================================================
# IMPORTS
# =============================================================================

import ctypes
import logging
import os
import platform
import sys

# =============================================================================
# LOGGING
# =============================================================================

LOGGER = logging.getLogger(__name__)

# =============================================================================
# FUNCTIONS
# =============================================================================


def is_elevated() -> bool:
    """Check if the current process is running with elevated privileges.

    Returns:
        bool: True if running as admin/root, False otherwise.

    """
    try:
        if hasattr(os, "geteuid"):
            # Unix-like systems (Linux, macOS)
            return os.geteuid() == 0
        elif platform.system().lower() == "windows":
            # Windows systems
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        else:
            # Other or unsupported systems
            return False
    except Exception as error:
        # Fail safely: assume not elevated on error
        LOGGER.debug("Error checking elevation: {}".format(error))
        return False


def show_elevated_permissions_dialog() -> None:
    """Display a security warning dialog if running with elevated permissions.

    Explain that Atlas must be run as a regular user, then exit the
    application. Provide fallback to console output if display module
    is unavailable.
    """
    LOGGER.error("Atlas should not be run with elevated permissions.")
    LOGGER.info("Please run as a regular user for security purposes.")

    try:
        from atlas.display.popup import show_warning

        show_warning(
            title="Caution",
            message="Elevated Permissions Detected",
            details=(
                "Atlas must be run without elevated privileges "
                "for security purposes.\n\n"
                "Please close this application and run it as a regular user."
            ),
        )
        sys.exit(1)

    except ImportError:
        # Fallback if display module is not available
        LOGGER.error("Display module not available, cannot show dialog")
        LOGGER.critical(
            "ERROR: Atlas must be run without elevated privileges "
            "for security purposes."
        )
        sys.exit(1)

    except Exception as error:
        LOGGER.error(
            "Failed to show elevated permissions dialog: %s",
            error,
            exc_info=True,
        )
        LOGGER.critical(
            "ERROR: Atlas must be run without elevated privileges "
            "for security purposes."
        )
        sys.exit(1)


# =============================================================================
# macOS — TCC / Full Disk Access
# =============================================================================

_TCC_TEST_PATH = os.path.join(
    os.path.expanduser("~"), "Library", "Safari"
)


def needs_full_disk_access() -> bool:
    """Check if macOS TCC blocks access to protected directories.

    Probes ~/Library/Safari — if the folder exists but cannot
    be listed, macOS TCC is restricting this process.  Returns
    False on non-macOS systems or when the folder is absent.

    Returns:
        bool: True if FDA is needed to read protected paths.

    """
    if platform.system() != "Darwin":
        return False

    path = _TCC_TEST_PATH
    if not os.path.isdir(path):
        return False

    try:
        os.listdir(path)
        return False
    except PermissionError:
        LOGGER.info(
            "macOS TCC blocked access to %s — FDA required", path
        )
        return True
    except OSError:
        return False


def show_full_disk_access_dialog() -> bool:
    """Prompt the user to grant Full Disk Access on macOS.

    Uses the existing Atlas popup system.  If the user clicks
    **Yes**, System Preferences opens to the FDA pane and the
    function returns True (caller should abort the scan).
    If **No**, returns False (caller should skip protected
    browsers and proceed).

    Returns:
        bool: True if the user chose to open System Preferences
              (scan should NOT start).  False if they chose to
              skip (scan should continue without protected data).

    """
    try:
        from atlas.display.popup import show_question

        opened = show_question(
            title="Atlas",
            message="Full Disk Access Requested",
            details=(
                "Full Disk Access is optional. Other browsers "
                "will back up normally without it.\n\n"
                "Click Yes to open System Preferences for Safari, "
                "or No to skip Safari and continue."
            ),
        )

        if opened:
            _open_fda_preferences()

        return opened

    except ImportError:
        LOGGER.warning(
            "Display module unavailable; skipping FDA dialog"
        )
        return False

    except Exception as error:
        LOGGER.error(
            "Failed to show FDA dialog: %s",
            error,
            exc_info=True,
        )
        return False


def _open_fda_preferences() -> None:
    """Open macOS System Preferences to the FDA pane."""
    import subprocess

    try:
        subprocess.Popen(  # noqa: S603
            [
                "open",
                "x-apple.systempreferences:"
                "com.apple.preference.security"
                "?Privacy_AllFiles",
            ]
        )
        LOGGER.info("Opened System Preferences -> FDA pane")
    except Exception as error:
        LOGGER.error(
            "Could not open System Preferences: %s", error
        )
