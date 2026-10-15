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


def test_get_os_key_macos() -> None:
    """Verify get_os_key returns Macos when platform.system is Darwin."""
    with patch("platform.system", return_value="Darwin"):
        assert system.get_os_key() == "Macos"


def test_is_junction_non_windows() -> None:
    """Verify is_junction returns False on non-Windows platforms."""
    with patch("os.name", "posix"):
        assert system.is_junction("/some/path") is False


def test_is_junction_windows_detection() -> None:
    """Verify is_junction identifies reparse points on Windows."""
    from unittest.mock import MagicMock

    mock_stat = MagicMock()
    mock_stat.st_reparse_tag = 0xA0000003
    mock_stat.st_file_attributes = 1024

    with patch("os.name", "nt"):
        with patch("os.path.isjunction", return_value=True):
            assert system.is_junction("C:\\dummy\\junction") is True

    with patch("os.name", "nt"), patch.object(
        system.os.path, "isjunction", None, create=True
    ):
        with patch("os.lstat", return_value=mock_stat):
            assert system.is_junction("C:\\dummy\\junction") is True
