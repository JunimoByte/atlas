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
import site
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# =============================================================================
# LOGGING
# =============================================================================

LOGGER = logging.getLogger(__name__)

# =============================================================================
# FUNCTIONS
# =============================================================================


def _get_installed_data_base_path() -> Optional[str]:
    """Find a wheel data directory relative to the installed package."""
    module_path = Path(os.path.abspath(__file__))
    for parent in module_path.parents:
        config_dir = parent / "share" / "atlas" / "configs"
        if config_dir.is_dir():
            return str(config_dir.parent)

    return None


def _get_base_path() -> str:
    """Resolve config root for development, installed, and frozen builds."""
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", os.getcwd())

    candidates = (
        os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")),
        _get_installed_data_base_path(),
        sys.prefix,
        os.path.join(sys.prefix, "share", "atlas"),
        os.path.join(site.getuserbase(), "share", "atlas"),
        "/app",
    )
    for candidate in candidates:
        if candidate and os.path.isdir(os.path.join(candidate, "configs")):
            return candidate

    return os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))


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

        with open(json_path, "r", encoding="utf-8-sig") as file_handle:
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
