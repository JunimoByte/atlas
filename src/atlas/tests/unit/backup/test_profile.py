"""Atlas | Tests | Backup | Profile Management.

Unit tests for backup/profile.py.
Covers path expansion, wildcard resolution, profile validation, and lookup.
"""

# =============================================================================
# IMPORTS
# =============================================================================

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
# FIXTURES
# =============================================================================


@pytest.fixture(autouse=True)
def clear_path_cache() -> None:
    """Clear the profile path cache before each test."""
    profile_module._PATH_CACHE.clear()
    yield
    profile_module._PATH_CACHE.clear()


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


# =============================================================================
# TESTS — Validate profile path
# =============================================================================


def test_validate_profile_path_returns_none_for_missing(
    tmp_path: Path
) -> None:
    """Verify that None is returned for nonexistent paths."""
    assert _validate_profile_path(tmp_path / "nonexistent", None) is None


def test_validate_profile_path_no_signature_required(tmp_path: Path) -> None:
    """Verify that any existing directory is accepted without a signature."""
    assert _validate_profile_path(tmp_path, False) == str(tmp_path.resolve())


def test_validate_profile_path_with_matching_signature(tmp_path: Path) -> None:
    """Verify that validation passes with a matching signature."""
    (tmp_path / "Preferences").write_text("{}")
    assert _validate_profile_path(tmp_path, "Preferences") is not None


def test_validate_profile_path_with_missing_signature(tmp_path: Path) -> None:
    """Verify that validation fails when the signature is absent."""
    assert _validate_profile_path(tmp_path, "Preferences") is None


def test_validate_profile_path_with_list_signature_any_match(
    tmp_path: Path
) -> None:
    """Verify that any matching signature in a list satisfies validation."""
    (tmp_path / "Bookmarks").write_text("{}")
    assert _validate_profile_path(
        tmp_path, ["Preferences", "Bookmarks"]
    ) is not None


def test_validate_profile_path_caches_result(tmp_path: Path) -> None:
    """Verify that validation results are cached."""
    (tmp_path / "Preferences").write_text("{}")
    result1 = _validate_profile_path(tmp_path, "Preferences")
    result2 = _validate_profile_path(tmp_path, "Preferences")
    assert result1 == result2
    assert len(profile_module._PATH_CACHE) >= 1


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
                    "Signature": "Preferences"
                }
            ]
        }
    }

    with patch.object(
        profile_module,
        "_expand_path_by_type",
        return_value=[profile_dir]
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
        profile_module,
        "_expand_path_by_type",
        return_value=[profile_dir]
    ):
        result = find_profile(
            "TestBrowser", "windows", browsers_data=fake_browsers
        )

    assert len(result) == len(set(r.lower() for r in result))


# =============================================================================
# TESTS — Get browser name from path
# =============================================================================


def test_get_browser_name_from_path_returns_unknown_for_empty() -> None:
    """Verify that 'Unknown' is returned for empty paths."""
    assert get_browser_name_from_path("") == "Unknown"


def test_get_browser_name_from_path_returns_unknown_for_no_match(
    tmp_path: Path
) -> None:
    """Verify that 'Unknown' is returned when no browser matches the path."""
    result = get_browser_name_from_path(
        str(tmp_path / "SomeRandomPath"),
        browsers_data={}
    )
    assert result == "Unknown"


# =============================================================================
# TEST EXECUTION
# =============================================================================

if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
