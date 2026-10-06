"""Atlas | Tests | Packages | System.

Unit tests for OS normalization and system identification.
"""

from unittest.mock import patch

import pytest

from atlas.lib import system


@pytest.mark.parametrize(
    "raw_os,expected",
    [
        ("Linux", "Linux"),
        ("linux", "Linux"),
        ("Windows", "Windows"),
        ("win32", "Windows"),
        ("FreeBSD", "BSD"),
        ("OpenBSD", "BSD"),
        ("NetBSD", "BSD"),
        ("DragonFly", "BSD"),
        ("bsd", "BSD"),
        ("Darwin", "Macos"),
        ("macos", "Macos"),
        ("mac", "Macos"),
        ("SunOS", "SOLARIS"),
        ("sunos", "SOLARIS"),
        ("solaris", "SOLARIS"),
        ("illumos", "SOLARIS"),
    ],
)
def test_normalize_os_key(raw_os: str, expected: str) -> None:
    """Verify raw OS identifiers normalize to their correct config keys."""
    assert system.normalize_os_key(raw_os) == expected


def test_get_os_key_solaris() -> None:
    """Verify get_os_key returns SOLARIS when platform.system is SunOS."""
    with patch("platform.system", return_value="SunOS"):
        assert system.get_os_key() == "SOLARIS"
