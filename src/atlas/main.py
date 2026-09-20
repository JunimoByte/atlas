"""Atlas | Entry Point.

Main entry point for the Atlas browser backup application.
Handles initialization, configuration verification, UI setup, and execution.
"""

# =============================================================================
# IMPORTS
# =============================================================================

import logging
import sys

from atlas.args import parse_args

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


def main() -> None:
    """Launch Atlas.

    Routes execution to either the CLI or GUI based on parsed arguments.
    """
    args = parse_args()

    if args.cli:
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
