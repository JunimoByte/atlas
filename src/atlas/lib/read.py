"""
Atlas | Packages | Safe JSON Loader

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


def _get_base_path() -> str:
    """Resolve project root path for dev and frozen environments."""
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", os.getcwd())

    return os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../../..")
    )


def load_json(filename: str, config_dir: str = "configs") -> Dict[str, Any]:
    """Safely load a JSON configuration file and return parsed data.

    Works in development, pip installs, and PyInstaller bundles.

    Args:
        filename (str): Name of the JSON file.
        config_dir (str): Directory containing the file.

    Returns:
        Dict[str, Any]: Parsed JSON data, or empty dict on failure.
    """
    try:
        base_path = _get_base_path()
        json_path = os.path.join(base_path, config_dir, filename)

        if not os.path.isfile(json_path):
            LOGGER.warning("JSON file not found: %s", json_path)
            return {}

        with open(json_path, "r", encoding="utf-8") as file_handle:
            data = json.load(file_handle)

        if not isinstance(data, dict):
            LOGGER.warning(
                "JSON file %s is not a dictionary. Returning empty dict.",
                filename,
            )
            return {}

        return data

    except json.JSONDecodeError:
        LOGGER.error(
            "JSON decode error in %s",
            filename,
            exc_info=True,
        )
        return {}

    except Exception:
        LOGGER.error(
            "Unexpected error loading %s",
            filename,
            exc_info=True,
        )
        return {}
