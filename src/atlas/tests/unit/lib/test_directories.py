"""Atlas | Tests | Packages | Directories.

Unit tests for directories.py.
"""

# =============================================================================
# IMPORTS
# =============================================================================

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from atlas.lib import directories

# =============================================================================
# TESTS — get_downloads_dir
# =============================================================================


def test_get_downloads_dir_returns_path(tmp_path: Path) -> None:
    """Verify get_downloads_dir returns a usable Path object."""
    dl = tmp_path / "Downloads"

    with patch(
        "atlas.lib.directories.platform.system",
        return_value="Linux",
    ), patch(
        "atlas.lib.directories._get_linux_candidates",
        return_value=[dl],
    ):
        result = directories.get_downloads_dir()
        assert isinstance(result, Path)
        assert result.exists()


def test_get_downloads_dir_creates_directory(
    tmp_path: Path,
) -> None:
    """Verify the Downloads directory is created if missing."""
    target = tmp_path / "NewDownloads"
    assert not target.exists()

    with patch(
        "atlas.lib.directories.platform.system",
        return_value="Darwin",
    ), patch(
        "atlas.lib.directories._get_downloads_posix_fallback",
        return_value=target,
    ):
        result = directories.get_downloads_dir()
        assert result.exists()
        assert result == target.resolve()


def test_get_downloads_dir_linux_xdg_file(
    tmp_path: Path,
) -> None:
    """Verify XDG user-dirs.dirs file is parsed on Linux."""
    downloads = tmp_path / "XDGDownloads"
    downloads.mkdir()

    with patch(
        "atlas.lib.directories.platform.system",
        return_value="Linux",
    ), patch(
        "atlas.lib.directories._parse_xdg_user_dirs_file",
        return_value=downloads,
    ), patch(
        "atlas.lib.directories._read_xdg_env_var",
        return_value=None,
    ):
        result = directories.get_downloads_dir()
        assert result == downloads.resolve()


def test_get_downloads_dir_linux_env_var(
    tmp_path: Path,
) -> None:
    """Verify XDG_DOWNLOAD_DIR env var is read on Linux."""
    downloads = tmp_path / "EnvDownloads"
    downloads.mkdir()

    with patch(
        "atlas.lib.directories.platform.system",
        return_value="Linux",
    ), patch(
        "atlas.lib.directories._parse_xdg_user_dirs_file",
        return_value=None,
    ), patch(
        "atlas.lib.directories._read_xdg_env_var",
        return_value=downloads,
    ):
        result = directories.get_downloads_dir()
        assert result == downloads.resolve()


def test_get_downloads_dir_linux_fallback(
    tmp_path: Path,
) -> None:
    """Verify ~/Downloads fallback on minimal Linux systems."""
    fallback = tmp_path / "Downloads"

    with patch(
        "atlas.lib.directories.platform.system",
        return_value="Linux",
    ), patch(
        "atlas.lib.directories._parse_xdg_user_dirs_file",
        return_value=None,
    ), patch(
        "atlas.lib.directories._read_xdg_env_var",
        return_value=None,
    ), patch(
        "atlas.lib.directories._get_downloads_posix_fallback",
        return_value=fallback,
    ):
        result = directories.get_downloads_dir()
        assert result == fallback.resolve()


def test_get_downloads_dir_windows_known_folder(
    tmp_path: Path,
) -> None:
    """Verify Windows SHGetKnownFolderPath is used first."""
    win_downloads = tmp_path / "WinDownloads"
    win_downloads.mkdir()

    with patch(
        "atlas.lib.directories.platform.system",
        return_value="Windows",
    ), patch(
        "atlas.lib.directories._shell_known_folder_path",
        return_value=win_downloads,
    ), patch(
        "atlas.lib.directories._shell_folder_path_registry",
        return_value=None,
    ):
        result = directories.get_downloads_dir()
        assert result == win_downloads.resolve()


def test_get_downloads_dir_windows_registry_fallback(
    tmp_path: Path,
) -> None:
    """Verify Windows registry is used when Shell API fails."""
    reg_downloads = tmp_path / "RegDownloads"
    reg_downloads.mkdir()

    with patch(
        "atlas.lib.directories.platform.system",
        return_value="Windows",
    ), patch(
        "atlas.lib.directories._shell_known_folder_path",
        return_value=None,
    ), patch(
        "atlas.lib.directories._shell_folder_path_registry",
        return_value=reg_downloads,
    ):
        result = directories.get_downloads_dir()
        assert result == reg_downloads.resolve()


def test_get_downloads_dir_exe_adjacent_last_resort(
    tmp_path: Path,
) -> None:
    """Verify exe-adjacent fallback when all downloads fail."""
    exe_dir = tmp_path / "output"

    with patch(
        "atlas.lib.directories.platform.system",
        return_value="Linux",
    ), patch(
        "atlas.lib.directories._get_linux_candidates",
        return_value=[],
    ), patch(
        "atlas.lib.directories._get_exe_adjacent_dir",
        return_value=exe_dir,
    ):
        result = directories.get_downloads_dir()
        assert result == exe_dir.resolve()
        assert result.exists()


# =============================================================================
# TESTS — XDG helpers
# =============================================================================


def test_parse_xdg_user_dirs_file(tmp_path: Path) -> None:
    """Verify parsing a real user-dirs.dirs file."""
    config_dir = tmp_path / ".config"
    config_dir.mkdir()
    dirs_file = config_dir / "user-dirs.dirs"
    dirs_file.write_text(
        'XDG_DOWNLOAD_DIR="$HOME/MyDownloads"\n',
        encoding="utf-8",
    )

    with patch.object(Path, "home", return_value=tmp_path), \
         patch.dict(
             "os.environ",
             {"XDG_CONFIG_HOME": str(config_dir)},
         ):
        result = directories._parse_xdg_user_dirs_file()
        assert result is not None
        assert result == tmp_path / "MyDownloads"


def test_parse_xdg_user_dirs_file_missing() -> None:
    """Verify None is returned when user-dirs.dirs is absent."""
    with patch.dict(
        "os.environ",
        {"XDG_CONFIG_HOME": "/nonexistent/path"},
    ):
        result = directories._parse_xdg_user_dirs_file()
        assert result is None


def test_read_xdg_env_var_absolute(tmp_path: Path) -> None:
    """Verify reading an absolute XDG_DOWNLOAD_DIR env var."""
    target = tmp_path / "EnvDir"
    with patch.dict(
        "os.environ", {"XDG_DOWNLOAD_DIR": str(target)}
    ):
        result = directories._read_xdg_env_var()
        assert result == target


def test_read_xdg_env_var_relative() -> None:
    """Verify relative XDG_DOWNLOAD_DIR is rejected."""
    with patch.dict(
        "os.environ", {"XDG_DOWNLOAD_DIR": "relative/path"}
    ):
        result = directories._read_xdg_env_var()
        assert result is None


def test_read_xdg_env_var_unset() -> None:
    """Verify None when XDG_DOWNLOAD_DIR is not set."""
    with patch.dict("os.environ", {}, clear=True):
        result = directories._read_xdg_env_var()
        assert result is None


# =============================================================================
# TESTS — _get_exe_adjacent_dir
# =============================================================================


def test_exe_adjacent_dir_frozen(tmp_path: Path) -> None:
    """Verify frozen mode returns directory next to sys.executable."""
    fake_exe = tmp_path / "Atlas.exe"

    with patch.object(
        sys, "frozen", True, create=True
    ), patch.object(
        sys, "executable", str(fake_exe)
    ):
        result = directories._get_exe_adjacent_dir()
        assert result == tmp_path / "output"


def test_exe_adjacent_dir_dev() -> None:
    """Verify dev mode returns a path relative to the src root."""
    with patch.object(
        sys, "frozen", False, create=True
    ):
        result = directories._get_exe_adjacent_dir()
        assert result.name == "output"
        assert result.is_absolute()


# =============================================================================
# TEST EXECUTION
# =============================================================================

if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
