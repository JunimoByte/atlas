"""Atlas | Tests | Backup | Profile Management.

Unit tests for backup/profile.py.
Covers path expansion, wildcard resolution, profile validation, and lookup.
"""

# =============================================================================
# IMPORTS
# =============================================================================

import errno
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

import atlas.backup.profile as profile_module
from atlas.backup.profile import (
    _expand_wildcard,
    _validate_profile_path,
    find_profile,
    get_browser_name_from_path,
)

# =============================================================================
# TESTS — Expand wildcard
# =============================================================================


def test_expand_wildcard_no_wildcard_returns_path(tmp_path: Path) -> None:
    """Verify that literal paths are returned when no wildcards are present."""
    sub = tmp_path / "profiles"
    sub.mkdir()
    assert sub in _expand_wildcard(tmp_path, Path("profiles"))


def test_expand_wildcard_matches_glob(tmp_path: Path) -> None:
    """Verify wildcard matching for directory segments."""
    (tmp_path / "Profile 1").mkdir()
    (tmp_path / "Profile 2").mkdir()
    assert len(_expand_wildcard(tmp_path, Path("Profile *"))) == 2


def test_expand_wildcard_nonexistent_base(tmp_path: Path) -> None:
    """Verify that an empty list is returned for nonexistent base paths."""
    assert _expand_wildcard(tmp_path / "missing", Path("sub")) == []


def test_expand_wildcard_empty_rel_path_returns_base(tmp_path: Path) -> None:
    """Verify that the base path is returned for an empty relative path."""
    assert tmp_path in _expand_wildcard(tmp_path, Path(""))


def test_expand_wildcard_surfaces_unexpected_io_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Unexpected I/O failures must not look like an absent profile."""
    original_stat = profile_module.os.stat

    def broken_stat(
        path: object, *args: object, **kwargs: object
    ) -> object:
        if Path(path) == tmp_path:
            raise OSError(errno.EIO, "I/O failure")
        return original_stat(path, *args, **kwargs)

    monkeypatch.setattr(profile_module.os, "stat", broken_stat)

    with pytest.raises(profile_module.ProfileScanError):
        _expand_wildcard(tmp_path, Path(""))


def test_expand_wildcard_surfaces_candidate_io_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A wildcard candidate I/O error must not hide a profile."""
    candidate = tmp_path / "Profile 1"
    candidate.mkdir()
    original_stat = profile_module.os.stat

    def broken_stat(
        path: object, *args: object, **kwargs: object
    ) -> object:
        if Path(path) == candidate:
            raise OSError(errno.EIO, "I/O failure")
        return original_stat(path, *args, **kwargs)

    monkeypatch.setattr(profile_module.os, "stat", broken_stat)

    with pytest.raises(profile_module.ProfileScanError):
        _expand_wildcard(tmp_path, Path("Profile *"))


def test_expand_path_by_type_rechecks_wildcards(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Wildcard discovery reflects profiles created after an earlier scan."""
    profiles_dir = tmp_path / "Profiles"
    profiles_dir.mkdir()
    (profiles_dir / "Profile 1").mkdir()
    monkeypatch.setattr(
        profile_module,
        "PATH_TYPES",
        {"Windows": {"APPDATA": [str(tmp_path)]}},
    )

    first = profile_module._expand_path_by_type(
        "APPDATA", "Profiles/Profile *", "Windows"
    )
    (profiles_dir / "Profile 2").mkdir()
    second = profile_module._expand_path_by_type(
        "APPDATA", "Profiles/Profile *", "Windows"
    )

    assert len(first) == 1
    assert len(second) == 2


# =============================================================================
# TESTS — Validate profile path
# =============================================================================


def test_validate_profile_path_returns_none_for_missing(
    tmp_path: Path,
) -> None:
    """Verify that None is returned for nonexistent paths."""
    assert _validate_profile_path(tmp_path / "nonexistent", None) is None


def test_validate_profile_path_no_signature_required(tmp_path: Path) -> None:
    """Verify that any existing directory is accepted without a signature."""
    assert _validate_profile_path(tmp_path, False) == str(tmp_path.resolve())


def test_validate_profile_path_rejects_file_without_signature(
    tmp_path: Path,
) -> None:
    """A profile candidate must be a directory even without a signature."""
    profile_file = tmp_path / "not-a-directory"
    profile_file.write_text("data", encoding="utf-8")

    assert _validate_profile_path(profile_file, False) is None


def test_validate_profile_path_surfaces_late_io_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An I/O failure after the initial existence check must fail the scan."""
    original_stat = profile_module.os.stat
    stat_calls = 0

    def unstable_stat(
        path: object, *args: object, **kwargs: object
    ) -> object:
        nonlocal stat_calls
        if Path(path) == tmp_path:
            stat_calls += 1
            if stat_calls >= 2:
                raise OSError(errno.EIO, "I/O failure")
        return original_stat(path, *args, **kwargs)

    monkeypatch.setattr(profile_module.os, "stat", unstable_stat)

    with pytest.raises(profile_module.ProfileScanError):
        _validate_profile_path(tmp_path, False)


def test_validate_profile_path_with_matching_signature(tmp_path: Path) -> None:
    """Verify that validation passes with a matching signature."""
    (tmp_path / "Preferences").write_text("{}")
    assert _validate_profile_path(tmp_path, "Preferences") is not None


def test_validate_profile_path_with_missing_signature(tmp_path: Path) -> None:
    """Verify that validation fails when the signature is absent."""
    assert _validate_profile_path(tmp_path, "Preferences") is None


def test_validate_profile_path_with_list_signature_any_match(
    tmp_path: Path,
) -> None:
    """Verify that any matching signature in a list satisfies validation."""
    (tmp_path / "Bookmarks").write_text("{}")
    assert (
        _validate_profile_path(tmp_path, ["Preferences", "Bookmarks"])
        is not None
    )


def test_validate_profile_path_rechecks_filesystem_state(
    tmp_path: Path,
) -> None:
    """Validation must reflect profile creation and signature removal."""
    profile_dir = tmp_path / "Profile"

    assert _validate_profile_path(profile_dir, "Preferences") is None

    profile_dir.mkdir()
    signature = profile_dir / "Preferences"
    signature.write_text("{}")
    assert _validate_profile_path(profile_dir, "Preferences") == str(
        profile_dir.resolve()
    )

    signature.unlink()
    assert _validate_profile_path(profile_dir, "Preferences") is None


# =============================================================================
# TESTS — Find profile
# =============================================================================


def test_find_profile_returns_empty_for_unknown_browser() -> None:
    """Verify that unknown browsers return an empty list."""
    assert find_profile("UnknownBrowser", "windows", browsers_data={}) == []


def test_find_profile_returns_empty_for_empty_os() -> None:
    """Verify that an empty OS string returns no profiles."""
    assert find_profile("Chrome", "", browsers_data={"Chrome": {}}) == []


def test_find_profile_discovers_real_path(tmp_path: Path) -> None:
    """Verify that profiles are discovered when paths and signatures match."""
    profile_dir = tmp_path / "ProfileDir"
    profile_dir.mkdir()
    (profile_dir / "Preferences").write_text("{}")

    fake_browsers = {
        "TestBrowser": {
            "Windows": [
                {
                    "Path": str(profile_dir),
                    "Type": "APPDATA",
                    "Signature": "Preferences",
                }
            ]
        }
    }

    with patch.object(
        profile_module, "_expand_path_by_type", return_value=[profile_dir]
    ):
        result = find_profile(
            "TestBrowser", "windows", browsers_data=fake_browsers
        )

    assert len(result) >= 1


def test_find_profile_deduplicates_paths(tmp_path: Path) -> None:
    """Verify that resolved profile paths are deduplicated."""
    profile_dir = tmp_path / "Profile"
    profile_dir.mkdir()
    (profile_dir / "Prefs").write_text("{}")

    fake_browsers = {
        "TestBrowser": {
            "Windows": [
                {"Path": str(profile_dir), "Type": "A", "Signature": "Prefs"},
                {"Path": str(profile_dir), "Type": "A", "Signature": "Prefs"},
            ]
        }
    }

    with patch.object(
        profile_module, "_expand_path_by_type", return_value=[profile_dir]
    ):
        result = find_profile(
            "TestBrowser", "windows", browsers_data=fake_browsers
        )

    assert len(result) == len(set(r.lower() for r in result))


def test_find_profile_solaris_firefox(tmp_path: Path) -> None:
    """Verify that Firefox profiles are discovered on Solaris / SunOS."""
    profile_dir = tmp_path / ".mozilla" / "firefox"
    profile_dir.mkdir(parents=True)
    (profile_dir / "profiles.ini").write_text("[Profile0]\nName=default\n")

    fake_browsers = {
        "Firefox": {
            "SOLARIS": [
                {
                    "Path": ".mozilla/firefox",
                    "Type": "HOME",
                    "Signature": ["profiles.ini"],
                }
            ]
        }
    }

    with patch.object(
        profile_module, "_expand_path_by_type", return_value=[profile_dir]
    ):
        result = find_profile("Firefox", "SunOS", browsers_data=fake_browsers)

    assert len(result) == 1
    assert str(profile_dir.resolve()) in result[0]


def test_find_profile_macos_chrome(tmp_path: Path) -> None:
    """Verify that Chrome profiles are discovered on macOS / Darwin."""
    profile_dir = tmp_path / "Google" / "Chrome"
    profile_dir.mkdir(parents=True)
    (profile_dir / "Local State").write_text("{}")

    fake_browsers = {
        "Google Chrome": {
            "Macos": [
                {
                    "Path": "Google/Chrome",
                    "Type": "APPDATA",
                    "Signature": ["Local State"],
                }
            ]
        }
    }

    with patch.object(
        profile_module, "_expand_path_by_type", return_value=[profile_dir]
    ):
        result = find_profile(
            "Google Chrome", "Darwin", browsers_data=fake_browsers
        )

    assert len(result) == 1
    assert str(profile_dir.resolve()) in result[0]


def test_find_profile_skips_unreadable_directory(tmp_path: Path) -> None:
    """Verify that unreadable directories (e.g. TCC) are skipped."""
    profile_dir = tmp_path / "Safari"
    profile_dir.mkdir(parents=True)

    fake_browsers = {
        "Safari": {
            "Macos": [
                {
                    "Path": "Safari",
                    "Type": "HOME",
                    "Signature": False,
                }
            ]
        }
    }

    with patch.object(
        profile_module, "_expand_path_by_type", return_value=[profile_dir]
    ):
        with patch(
            "os.scandir", side_effect=PermissionError("TCC locked")
        ):
            result = find_profile(
                "Safari", "Darwin", browsers_data=fake_browsers
            )

    assert result == []


def test_find_profile_linux_chromium_snap_current(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify Chromium profile discovered via snap current path."""
    snap_dir = tmp_path / "snap" / "chromium" / "current" / ".config"
    profile_dir = snap_dir / "chromium"
    profile_dir.mkdir(parents=True)
    (profile_dir / "Local State").write_text("{}")

    fake_browsers = {
        "Chromium": {
            "Linux": [
                {
                    "Type": "SNAP",
                    "Path": "chromium/current/.config/chromium",
                    "Signature": ["Local State"],
                }
            ]
        }
    }

    fake_types = {
        "Linux": {
            "SNAP": [str(tmp_path / "snap")]
        }
    }

    monkeypatch.setattr(profile_module, "PATH_TYPES", fake_types)
    result = find_profile(
        "Chromium", "Linux", browsers_data=fake_browsers
    )
    assert any(str(profile_dir.resolve()) in p for p in result)


# =============================================================================
# TESTS — Get browser name from path
# =============================================================================


def test_get_browser_name_from_path_returns_unknown_for_empty() -> None:
    """Verify that 'Unknown' is returned for empty paths."""
    assert get_browser_name_from_path("") == "Unknown"


def test_get_browser_name_from_path_returns_unknown_for_no_match(
    tmp_path: Path,
) -> None:
    """Verify that 'Unknown' is returned when no browser matches the path."""
    result = get_browser_name_from_path(
        str(tmp_path / "SomeRandomPath"), browsers_data={}
    )
    assert result == "Unknown"


# =============================================================================
# TEST EXECUTION
# =============================================================================

if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
