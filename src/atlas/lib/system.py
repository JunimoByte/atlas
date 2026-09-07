"""Atlas | Packages | System.

Centralized system identification and OS string normalization.
"""

import platform


def normalize_os_key(os_name: str) -> str:
    """Normalize a raw OS string into a stable configuration key.

    Maps BSD variants to 'BSD' and Darwin to 'Macos'.

    Args:
        os_name: Raw OS string (e.g., from platform.system()).

    Returns:
        str: Normalized OS key (e.g. 'Windows', 'Linux', 'Macos', 'BSD').

    """
    sys_name = os_name.lower()

    if sys_name in ("freebsd", "openbsd", "netbsd", "dragonfly"):
        return "BSD"

    if sys_name == "darwin":
        return "Macos"

    # Windows -> Windows, Linux -> Linux
    return sys_name.capitalize()


def get_os_key() -> str:
    """Return the normalized, capitalized OS name for the current system."""
    return normalize_os_key(platform.system())
