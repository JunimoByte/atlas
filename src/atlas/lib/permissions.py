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

from atlas.display.popup import show_warning

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
