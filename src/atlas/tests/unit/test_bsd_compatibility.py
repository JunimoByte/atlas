"""Atlas | Tests | Unit | BSD Compatibility.

Comprehensive unit tests verifying BSD subsystem behavior across
FreeBSD, OpenBSD, NetBSD, and DragonFly BSD environments.
"""

# =============================================================================
# IMPORTS
# =============================================================================

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from atlas.backup import profile
from atlas.compatibility import qt
from atlas.lib import browsers, directories, integration, permissions, system

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture(autouse=True)
def init_test_environment() -> None:
    """Ensure browser configuration is loaded before each test."""
    browsers.verify_entries()
    yield


# =============================================================================
# TESTS — SYSTEM NORMALIZATION
# =============================================================================


@pytest.mark.parametrize(
    "bsd_flavor",
    ["FreeBSD", "OpenBSD", "NetBSD", "DragonFly", "freebsd", "openbsd"],
)
def test_bsd_os_normalization(bsd_flavor: str) -> None:
    """Verify all BSD platform variants normalize to the 'BSD' config key."""
    assert system.normalize_os_key(bsd_flavor) == "BSD"


# =============================================================================
# TESTS — DOWNLOADS RESOLUTION ON BSD
# =============================================================================


def test_bsd_downloads_resolution_via_user_dirs(tmp_path: Path) -> None:
    """Verify Downloads resolution on BSD respects XDG user-dirs."""
    config_dir = tmp_path / ".config"
    config_dir.mkdir(parents=True)
    custom_downloads = tmp_path / "BSDDownloads"

    dirs_file = config_dir / "user-dirs.dirs"
    dirs_file.write_text(
        f'XDG_DOWNLOAD_DIR="{custom_downloads}"\n',
        encoding="utf-8",
    )

    with patch("platform.system", return_value="FreeBSD"), patch.dict(
        os.environ, {"XDG_CONFIG_HOME": str(config_dir)}
    ):
        resolved = directories.get_downloads_dir()
        assert resolved == custom_downloads.resolve()
        assert resolved.exists()


def test_bsd_downloads_resolution_fallback(tmp_path: Path) -> None:
    """Verify BSD falls back to ~/Downloads when XDG config is missing."""
    mock_home = tmp_path / "home_user"
    mock_home.mkdir()
    expected_downloads = mock_home / "Downloads"

    with patch("platform.system", return_value="OpenBSD"), patch.dict(
        os.environ,
        {
            "XDG_CONFIG_HOME": str(mock_home / "nonexistent"),
            "HOME": str(mock_home),
            "USERPROFILE": str(mock_home),
        },
    ), patch.object(Path, "home", return_value=mock_home):
        resolved = directories.get_downloads_dir()
        assert resolved == expected_downloads.resolve()
        assert resolved.exists()


# =============================================================================
# TESTS — BROWSER PROFILE DISCOVERY ON BSD
# =============================================================================


def test_bsd_find_profile_firefox(tmp_path: Path) -> None:
    """Verify Firefox profile discovery under simulated BSD."""
    mock_home = tmp_path / "user"
    ff_dir = mock_home / ".mozilla" / "firefox"
    ff_dir.mkdir(parents=True)
    (ff_dir / "profiles.ini").write_text("[Profile0]\nName=default\n")

    with patch.dict(
        os.environ,
        {"HOME": str(mock_home), "USERPROFILE": str(mock_home)},
    ):
        profiles = profile.find_profile("Firefox", "FreeBSD")
        assert len(profiles) >= 1
        assert any(".mozilla" in p for p in profiles)


def test_bsd_find_profile_chromium(tmp_path: Path) -> None:
    """Verify Chromium profile discovery on OpenBSD using ~/.config."""
    mock_home = tmp_path / "user"
    chrom_dir = mock_home / ".config" / "chromium"
    chrom_dir.mkdir(parents=True)
    (chrom_dir / "Local State").write_text("{}")

    with patch.dict(
        os.environ,
        {"HOME": str(mock_home), "USERPROFILE": str(mock_home)},
    ):
        profiles = profile.find_profile("Chromium", "OpenBSD")
        assert len(profiles) >= 1
        assert any("chromium" in p for p in profiles)


# =============================================================================
# TESTS — PERMISSIONS ON BSD
# =============================================================================


def test_bsd_is_elevated_root() -> None:
    """Verify is_elevated returns True when geteuid is 0 on BSD."""
    with patch("os.geteuid", return_value=0, create=True), patch(
        "platform.system", return_value="FreeBSD"
    ):
        assert permissions.is_elevated() is True


def test_bsd_is_elevated_standard_user() -> None:
    """Verify is_elevated returns False for regular user UIDs on BSD."""
    with patch("os.geteuid", return_value=1001, create=True), patch(
        "platform.system", return_value="FreeBSD"
    ):
        assert permissions.is_elevated() is False


# =============================================================================
# TESTS — QT COMPATIBILITY ON BSD
# =============================================================================


def test_bsd_qt_backend_defaults_to_xcb() -> None:
    """Verify QT_QPA_PLATFORM is automatically set to xcb on BSD."""
    with patch("sys.platform", "freebsd14"), patch.dict(
        os.environ, {}, clear=True
    ):
        qt._configure_linux_environment()
        assert os.environ.get("QT_QPA_PLATFORM") == "xcb"


def test_bsd_qt_backend_preserves_user_override() -> None:
    """Verify user-specified QT_QPA_PLATFORM is not overwritten on BSD."""
    with patch("sys.platform", "freebsd14"), patch.dict(
        os.environ, {"QT_QPA_PLATFORM": "wayland"}, clear=True
    ):
        qt._configure_linux_environment()
        assert os.environ.get("QT_QPA_PLATFORM") == "wayland"


# =============================================================================
# TESTS — DESKTOP INTEGRATION ON BSD
# =============================================================================


def test_bsd_open_folder_platform_dispatches_posix(tmp_path: Path) -> None:
    """Verify open_folder on BSD uses POSIX opener dispatch."""
    target = tmp_path / "output"
    target.mkdir()

    mock_run = MagicMock(return_value=True)
    with patch("platform.system", return_value="FreeBSD"), patch(
        "atlas.lib.integration._run_linux_open", mock_run
    ), patch("threading.Thread") as mock_thread:
        integration._open_folder_platform(target)
        assert mock_thread.called
        target_fn = mock_thread.call_args[1]["target"]
        target_fn()
        mock_run.assert_called_once_with(target)


def test_bsd_tiling_wm_detection() -> None:
    """Verify tiling window manager detection on BSD via SWAYSOCK."""
    with patch("sys.platform", "freebsd14"), patch.dict(
        os.environ, {"SWAYSOCK": "/tmp/sway-ipc.sock"}
    ):
        assert integration._is_tiling_window_manager() is True
