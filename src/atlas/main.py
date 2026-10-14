"""Atlas | Entry Point.

Main entry point for the Atlas browser backup application.
Handles initialization, configuration verification, UI setup, and execution.
"""

# =============================================================================
# IMPORTS
# =============================================================================

import logging
import sys

from atlas.args import is_cli_mode, parse_args

# =============================================================================
# LOGGING
# =============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

LOGGER = logging.getLogger(__name__)

# =============================================================================
# FUNCTIONS
# =============================================================================


def _attach_windows_console() -> None:
    """Attach to parent console on Windows for GUI-subsystem CLI runs."""
    if sys.platform != "win32":
        return
    try:
        import ctypes

        if ctypes.windll.kernel32.AttachConsole(-1):
            if sys.stdout is None or not hasattr(sys.stdout, "write"):
                sys.stdout = open(
                    "CONOUT$", "w", encoding="utf-8", errors="replace"
                )
            if sys.stderr is None or not hasattr(sys.stderr, "write"):
                sys.stderr = open(
                    "CONOUT$", "w", encoding="utf-8", errors="replace"
                )
    except Exception:
        pass


def main() -> None:
    """Launch Atlas.

    Routes execution to either the CLI or GUI based on parsed arguments.
    """
    args = parse_args()

    if getattr(args, "quiet", False) or getattr(args, "json", False):
        logging.getLogger().setLevel(logging.ERROR)

    if is_cli_mode(args):
        _attach_windows_console()
        from atlas.cli import run_cli

        sys.exit(run_cli(args))
    else:
        from atlas.gui import run_gui

        sys.exit(run_gui(args))


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
