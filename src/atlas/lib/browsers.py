"""Atlas | Packages | Browsers.

Compact browser loader and validator for Atlas.
"""

# =============================================================================
# IMPORTS
# =============================================================================

import logging
from types import MappingProxyType
from typing import Any, Dict, List, Mapping, Optional

from atlas.lib.read import load_json

# =============================================================================
# LOGGING
# =============================================================================

LOGGER = logging.getLogger(__name__)

# =============================================================================
# VARIABLES
# =============================================================================

BROWSERS: Dict[str, Any] = {}
_PATH_CACHE: Dict[str, List[str]] = {}
_REQUIRED_FIELDS: Dict[str, Any] = {
    "Path": str,
    "Type": str,
    "Signature": (str, bool, list),
}

# =============================================================================
# FUNCTIONS
# =============================================================================


def _validate_entry(
    entry: Dict[str, Any], browser: str, system: str
) -> List[str]:
    """Validate a single browser entry and return a list of errors."""
    errors = []
    if not isinstance(entry, dict):
        return ["❌ Entry in {} ({}) is not a dict".format(browser, system)]
    for field, ftype in _REQUIRED_FIELDS.items():
        val = entry.get(field)
        if val is None:
            errors.append(
                "❌ Missing {} in {} ({})".format(field, browser, system)
            )
            continue
        if isinstance(val, str) and not val.strip():
            errors.append(
                "❌ Empty {} in {} ({})".format(field, browser, system)
            )
        elif isinstance(val, list) and not all(
            isinstance(s, str) and s.strip() for s in val
        ):
            errors.append(
                "❌ Invalid list in {} of {} ({})".format(
                    field, browser, system
                )
            )
        elif not isinstance(val, ftype):
            errors.append(
                "❌ Wrong type for {} in {} ({})".format(
                    field, browser, system
                )
            )
    return errors


def verify_entries(
    browsers_json: Optional[Dict[str, Any]] = None,  # noqa: C901
    types_json: Optional[Dict[str, Any]] = None
) -> bool:
    """Load and validate browser configuration.

    Args:
        browsers_json (Optional[Dict[str, Any]]): Injected browser data.
        types_json (Optional[Dict[str, Any]]): Injected types data.

    Returns:
        bool: True if configuration is valid and loaded, False otherwise.

    """
    BROWSERS.clear()
    _PATH_CACHE.clear()

    try:
        data = (
            browsers_json if browsers_json is not None
            else load_json("browsers.json")
        )
        if not data:
            LOGGER.error("Failed to load browsers.json or it is empty.")
            return False

        cleaned: Dict[str, Any] = {}
        errors: List[str] = []

        for browser, systems in data.items():
            if (
                not isinstance(browser, str)
                or not isinstance(systems, dict)
                or not systems
            ):
                errors.append("❌ Invalid browser: {}".format(browser))
                continue
            clean_systems: Dict[str, Any] = {}
            for system, entries in systems.items():
                if not isinstance(entries, list) or not system.strip():
                    errors.append(
                        "❌ Invalid system {} in {}".format(system, browser)
                    )
                    continue
                clean_entries = []
                for entry in entries:
                    e_errors = _validate_entry(entry, browser, system)
                    if e_errors:
                        errors.extend(e_errors)
                        continue
                    clean_entries.append(entry)
                if clean_entries:
                    clean_systems[system] = clean_entries
            if clean_systems:
                cleaned[browser] = clean_systems

        for e in errors:
            LOGGER.warning(e)

        if not cleaned:
            LOGGER.error("No valid browser configurations found.")
            return False

        BROWSERS.update(cleaned)

        types_data = (
            types_json if types_json is not None else load_json("types.json")
        )
        for type_name, paths in types_data.items():
            if isinstance(paths, list):
                _PATH_CACHE[type_name.upper()] = [
                    str(p) for p in paths if isinstance(p, str)
                ]

        LOGGER.info("Loaded %d valid browsers.", len(BROWSERS))
        LOGGER.info("Loaded %d path types.", len(_PATH_CACHE))
        return True

    except Exception as error:
        LOGGER.error(
            "Unexpected error loading browser configuration: %s", error
        )
        return False


def grab() -> Mapping[str, Any]:
    """Return read-only browser configuration mapping.

    Returns:
        Mapping[str, Any]: Immutable view of cached browser data.

    """
    return MappingProxyType(BROWSERS)
