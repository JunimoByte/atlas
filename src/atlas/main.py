"""Atlas | Entry Point.

Main entry point for the Atlas browser backup application.
Handles initialization, configuration verification, UI setup, and execution.
"""

# =============================================================================
# IMPORTS
# =============================================================================

import logging
import sys

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import QApplication

from atlas.display import window
from atlas.lib import browsers, permissions, themes

# =============================================================================
# LOGGING
# =============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

LOGGER = logging.getLogger(__name__)

# =============================================================================
# FUNCTIONS
# =============================================================================


def main() -> None:
    """Launch Atlas.

    Validate permissions, check config, initialize PyQt6,
    set up the UI with theming, and run the event loop.
    Exit gracefully on errors.
    """
    # Permission validation
    if permissions.is_elevated():
        permissions.show_elevated_permissions_dialog()

    # Configuration verification
    if not browsers.verify_entries():
        LOGGER.error("Failed to load browser configuration. Exiting.")
        LOGGER.info(
            "Please check the configuration file and restart the application."
        )
        return

    # Application initialization
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    win = window.Window()
    themes.initialize(win)

    # Application execution
    win.show()
    LOGGER.info("Atlas has successfully started.")
    sys.exit(app.exec())


# Entry point
if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        LOGGER.error(
            "An unexpected error occurred: {}".format(error), exc_info=True
        )
        LOGGER.info(
            "Please check the error message and restart the application."
        )
        sys.exit(1)
