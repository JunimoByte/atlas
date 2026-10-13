"""Atlas | Profile Management.

Browser profile detection and path management for Atlas.
Locates valid browser profile directories and identifies browser types.
"""

# =============================================================================
# IMPORTS
# =============================================================================

import fnmatch
import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

from atlas.lib import browsers as browsers_list
from atlas.lib.read import load_json
from atlas.lib.system import get_os_key, normalize_os_key

# =============================================================================
# LOGGING
# =============================================================================

LOGGER = logging.getLogger(__name__)

# =============================================================================
# JSONS
# =============================================================================

try:
    PATH_TYPES = load_json("types.json")
except Exception:
    LOGGER.warning("Failed to load types.json", exc_info=True)
    PATH_TYPES = {}

# =============================================================================
# VARIABLES
# =============================================================================

_PATH_CACHE: Dict = {}

# =============================================================================
# FUNCTIONS
# =============================================================================


@lru_cache(maxsize=256)
def _expand_path_by_type(
    path_type: str, path: str, os_name: str
) -> List[Path]:
    """Expand paths using OS-specific type bases and handle wildcards.

    Args:
        path_type: The path type key (e.g. 'APPDATA', 'HOME').
        path: The relative path to expand beneath each base.
        os_name: The capitalised OS name (e.g. 'Windows', 'Linux').

    Returns:
        A deduplicated list of resolved candidate Paths.

    """
    os_types = PATH_TYPES.get(os_name, {})
    bases = os_types.get(path_type.upper(), [])
    expanded: List[Path] = []
    seen: Set[str] = set()  # Track normalised absolute paths

    for base in bases:
        base_path = Path(os.path.expandvars(os.path.expanduser(base)))
        candidates = _expand_wildcard(base_path, Path(path))
        for p in candidates:
            try:
                resolved = str(p.resolve())
            except Exception:
                resolved = str(p.absolute())
            if resolved not in seen:
                expanded.append(p)
                seen.add(resolved)

    return expanded


def _validate_profile_path(
    path: Path, signature: Union[str, List[str], None, bool]
) -> Optional[str]:
    """Validate profile path contains required signature(s)."""
    # Normalize path for platform-appropriate case comparison
    cache_key = (
        os.path.normcase(str(path)),
        tuple(signature) if isinstance(signature, list) else signature,
    )
    if cache_key in _PATH_CACHE:
        return _PATH_CACHE[cache_key]

    try:
        if not path.exists():
            _PATH_CACHE[cache_key] = None
            return None

        resolved_base = path.resolve()

        if resolved_base.is_dir():
            try:
                with os.scandir(resolved_base):
                    pass
            except (PermissionError, OSError):
                _PATH_CACHE[cache_key] = None
                return None

        if signature and isinstance(signature, (str, list)):
            signatures = (
                [signature] if isinstance(signature, str) else signature
            )
            if not any(
                (resolved_base / str(sig)).exists() for sig in signatures
            ):
                _PATH_CACHE[cache_key] = None
                return None

        _PATH_CACHE[cache_key] = str(resolved_base)
        return str(resolved_base)

    except Exception:
        LOGGER.debug(
            "Error checking path/signature for %s", path, exc_info=True
        )
        _PATH_CACHE[cache_key] = None
        return None


def _expand_wildcard(base: Path, rel_path: Path) -> List[Path]:
    """Recursively expand wildcards in each path segment."""
    # If no more segments, return base itself
    if not rel_path.parts:
        return [base] if base.exists() else []

    first, *rest = rel_path.parts
    matches: List[Path] = []

    # If first segment contains wildcard
    if "*" in first or "?" in first:
        if not base.exists():
            return []

        try:
            for entry in base.iterdir():
                if fnmatch.fnmatch(entry.name, first) and entry.is_dir():
                    matches.extend(_expand_wildcard(entry, Path(*rest)))
        except (OSError, PermissionError):
            return []
    else:
        # No wildcard, just join
        next_base = base / first
        matches.extend(_expand_wildcard(next_base, Path(*rest)))

    return matches


def _collect_entry_profiles(
    entry: Dict[str, Any],
    browser_name: str,
    os_key: str,
    seen_paths: Set[str],
) -> List[str]:
    """Extract and validate profile paths for a single configuration entry."""
    if not isinstance(entry, dict):
        LOGGER.warning("Skipping non-dict entry in %s", browser_name)
        return []

    raw_path = entry.get("Path")
    signature_file = entry.get("Signature")
    path_type = entry.get("Type")

    if not raw_path or signature_file is None or not path_type:
        LOGGER.error("Incomplete data for %s: %s", browser_name, entry)
        return []

    collected: List[str] = []
    candidate_paths = _expand_path_by_type(path_type, raw_path, os_key)
    for location in candidate_paths:
        result = _validate_profile_path(location, signature_file)
        if result:
            norm_path = os.path.normcase(result)
            if norm_path not in seen_paths:
                collected.append(result)
                seen_paths.add(norm_path)
    return collected


def find_profile(
    browser_name: str,
    operating_system: str,
    browsers_data: Optional[Dict[str, Any]] = None,
) -> List[str]:
    """Locate all valid profile directories for a browser on a given OS.

    Expand paths using type definitions from types.json.

    Args:
        browser_name: Name of the browser.
        operating_system: Operating system name.
        browsers_data: Optional dictionary of browser configurations.
                       If None, loads from atlas.lib.browsers.grab().

    Returns:
        List of valid profile directory paths.

    """
    if browsers_data is None:
        browsers_data = browsers_list.grab()

    if (
        not browser_name
        or browser_name not in browsers_data
        or not operating_system
    ):
        LOGGER.warning(
            "Invalid browser or OS: %s, %s", browser_name, operating_system
        )
        return []

    browser_data = browsers_data.get(browser_name, {})
    if not isinstance(browser_data, dict):
        LOGGER.warning(
            "Malformed configuration for browser %s", browser_name
        )
        return []

    os_key = normalize_os_key(operating_system)
    os_entries = browser_data.get(os_key, [])
    if not isinstance(os_entries, list):
        return []

    valid_profiles: List[str] = []
    seen_paths: Set[str] = set()

    for entry in os_entries:
        valid_profiles.extend(
            _collect_entry_profiles(entry, browser_name, os_key, seen_paths)
        )

    return valid_profiles


def _matches_entry_path(
    entry: Dict[str, Any], os_key: str, path_lower: str
) -> bool:
    """Check if a path matches an individual browser entry."""
    if not isinstance(entry, dict):
        return False
    raw_path = entry.get("Path")
    path_type = entry.get("Type")
    signature = entry.get("Signature")

    if not raw_path or not path_type:
        return False

    candidate_paths = _expand_path_by_type(path_type, raw_path, os_key)
    for location in candidate_paths:
        resolved = _validate_profile_path(location, signature)
        if resolved and path_lower.startswith(os.path.normcase(resolved)):
            return True
    return False


def get_browser_name_from_path(
    path_str: str,
    browsers_data: Optional[Dict[str, Any]] = None,
    operating_system: Optional[str] = None,
) -> str:
    """Return the browser name for a given profile path.

    Args:
        path_str: Profile path string.
        browsers_data: Optional dictionary of browser configurations.
                       If None, loads from atlas.lib.browsers.grab().
        operating_system: OS key to restrict lookup to. Defaults to the
                          current host OS via get_os_key().

    Returns:
        Browser name if matched, else "Unknown".

    """
    if not path_str:
        LOGGER.warning("Path was null")
        return "Unknown"

    if browsers_data is None:
        browsers_data = browsers_list.grab()

    os_key = (
        normalize_os_key(operating_system)
        if operating_system
        else get_os_key()
    )
    path_lower = os.path.normcase(str(Path(path_str)))

    for name, systems in browsers_data.items():
        if not isinstance(systems, dict):
            continue
        entries = systems.get(os_key, [])
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if _matches_entry_path(entry, os_key, path_lower):
                return name

    return "Unknown"
