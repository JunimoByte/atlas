"""Atlas | Packages | Safe JSON Loader.

Safely loads JSON configuration files. Works in both development and
PyInstaller bundles.
"""

# =============================================================================
# IMPORTS
# =============================================================================

import json
import logging
import os
import sys
from typing import Any, Dict

# =============================================================================
# LOGGING
# =============================================================================

LOGGER = logging.getLogger(__name__)

# =============================================================================
# FUNCTIONS
# =============================================================================


def load_json(filename: str, config_dir: str = "configs") -> Dict[str, Any]:
    """Safely load a JSON configuration file and return the parsed data.

    Handle path resolution for dev/frozen modes and error handling.

    Args:
        filename (str): Name of the JSON file.
        config_dir (str, optional): Directory containing the file.
            Defaults to "configs".

    Returns:
        Dict[str, Any]: Parsed JSON data, or empty dict on failure.

    """
    try:
        if getattr(sys, "frozen", False):
            base_path = getattr(sys, "_MEIPASS", os.getcwd())
        else:
            # Navigate from src/atlas/lib/ to project root (3 levels)
            base_path = os.path.dirname(
                os.path.dirname(
                    os.path.dirname(
                        os.path.dirname(os.path.abspath(__file__))
                    )
                )
            )

        json_path = os.path.join(base_path, config_dir, filename)

        if not os.path.exists(json_path):
            LOGGER.warning("JSON file not found: %s", json_path)
            return {}

        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            LOGGER.warning(
                "JSON file %s is not a dictionary. Returning empty dict.",
                filename,
            )
            return {}

        return data

    except json.JSONDecodeError:
        LOGGER.error("JSON decode error in %s", filename, exc_info=True)
        return {}
    except Exception:
        LOGGER.error("Unexpected error loading %s", filename, exc_info=True)
        return {}
