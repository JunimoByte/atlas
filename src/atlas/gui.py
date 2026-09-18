"""Atlas | GUI Entry Point.

Provides the PyQt graphical user interface initialization and event loop.
"""

# =============================================================================
# IMPORTS
# =============================================================================

import argparse
import logging
import sys

from atlas.compatibility.qt import QtCore, QtGui, QtWidgets
from atlas.display import window
from atlas.lib import browsers, permissions, themes

# =============================================================================
# LOGGING
# =============================================================================

LOGGER = logging.getLogger(__name__)

# =============================================================================
# FUNCTIONS
# =============================================================================


def run_gui(args: argparse.Namespace = None) -> int:
    """Launch the Atlas graphical user interface.

    Args:
        args: Parsed command-line arguments for future expandability.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    if permissions.is_elevated():
        permissions.show_elevated_permissions_dialog()

    if not browsers.verify_entries():
        LOGGER.error("Failed to load browser configuration. Exiting.")
        LOGGER.info(
            "Please check the configuration file and restart the application."
        )
        return 1

    has_policy_setter = hasattr(
        QtGui.QGuiApplication, "setHighDpiScaleFactorRoundingPolicy"
    )
    has_policy_enum = hasattr(QtCore.Qt, "HighDpiScaleFactorRoundingPolicy")

    if has_policy_setter and has_policy_enum:
        QtGui.QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
            QtCore.Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )

    app = QtWidgets.QApplication(sys.argv)
    win = window.Window()
    themes.initialize(win)

    win.show()
    LOGGER.info("Atlas GUI has successfully started.")
    return app.exec()
