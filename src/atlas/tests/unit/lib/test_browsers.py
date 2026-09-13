"""Atlas | Tests | Packages | Browsers.

Unit tests for the browser loader and validator.
"""

# =============================================================================
# IMPORTS
# =============================================================================

import os
import sys
from typing import Any, Dict, Generator

import pytest

from atlas.lib import browsers

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def sample_valid_browser() -> Dict[str, Any]:
    """Provide a sample valid browser configuration."""
    return {
        "Chrome": {
            "Windows": [
                {
                    "Path": os.path.join(
                        "mock_drive",
                        "Users",
                        "Test",
                        "AppData",
                        "Local",
                        "Google",
                        "Chrome",
                        "User Data",
                    ),
                    "Type": "profile",
                    "Signature": ["Preferences", "Bookmarks"],
                }
            ]
        }
    }


@pytest.fixture
def sample_invalid_browser() -> Dict[str, Any]:
    """Provide a sample invalid browser configuration (missing fields)."""
    return {
        "Firefox": {
            "Windows": [
                {"Path": "", "Type": 123, "Signature": None}  # Wrong type
            ]
        }
    }


@pytest.fixture(autouse=True)
def clear_globals_before_each_test() -> Generator[None, None, None]:
    """Clear BROWSERS and _PATH_CACHE before every test."""
    browsers.BROWSERS.clear()
    yield
    browsers.BROWSERS.clear()


# =============================================================================
# TESTS
# =============================================================================


def test_validate_entry_valid(sample_valid_browser: Dict[str, Any]) -> None:
    """Verify that valid entries return no errors."""
    entry = sample_valid_browser["Chrome"]["Windows"][0]
    errors = browsers._validate_entry(entry, "Chrome", "Windows")
    assert errors == []


def test_validate_entry_invalid(
    sample_invalid_browser: Dict[str, Any],
) -> None:
    """Verify that missing or incorrectly typed fields are caught."""
    entry = sample_invalid_browser["Firefox"]["Windows"][0]
    errors = browsers._validate_entry(entry, "Firefox", "Windows")
    assert len(errors) >= 1
    assert any("Empty Path" in e or "Wrong type" in e for e in errors)


def test_verify_entries_loads_valid_config(
    sample_valid_browser: Dict[str, Any],
) -> None:
    """Verify that valid configurations are loaded into memory."""
    result = browsers.verify_entries(
        browsers_json=sample_valid_browser
    )
    assert result is True
    assert "Chrome" in browsers.BROWSERS
    assert "Windows" in browsers.BROWSERS["Chrome"]


def test_verify_entries_rejects_invalid_config(
    sample_invalid_browser: Dict[str, Any],
) -> None:
    """Verify that invalid configurations are rejected."""
    result = browsers.verify_entries(
        browsers_json=sample_invalid_browser
    )
    assert result is False
    assert "Firefox" not in browsers.BROWSERS


def test_grab_returns_cached_data(
    sample_valid_browser: Dict[str, Any],
) -> None:
    """Verify that the cached browser data is returned."""
    browsers.BROWSERS.update(sample_valid_browser)
    cached = browsers.grab()
    assert cached == browsers.BROWSERS
    assert "Chrome" in cached


# =============================================================================
# TEST EXECUTION
# =============================================================================

if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
