"""Atlas | Tests | Display | Popup.

Unit tests for display/popup.py.
Covers constant maps, wrapper routing, and show() patching.
"""

# =============================================================================
# IMPORTS
# =============================================================================

import sys
from typing import Any

import pytest
from PyQt6.QtWidgets import QMessageBox

from atlas.display import popup

# =============================================================================
# TESTS — ICON_MAP
# =============================================================================


def test_icon_map_contains_all_keys() -> None:
    """Verify that ICON_MAP contains all expected keys."""
    expected = {"INFORMATION", "WARNING", "CRITICAL", "QUESTION"}
    assert expected == set(popup.ICON_MAP.keys())


def test_icon_map_values_are_qmessagebox_icons() -> None:
    """Verify that ICON_MAP values are QMessageBox icons."""
    for value in popup.ICON_MAP.values():
        assert isinstance(value, QMessageBox.Icon)


# =============================================================================
# TESTS — BUTTON_MAP
# =============================================================================


def test_button_map_contains_all_keys() -> None:
    """Verify that BUTTON_MAP contains all expected keys."""
    expected = {
        "ACKNOWLEDGE",
        "CONFIRM_DECLINE",
        "ACKNOWLEDGE_CANCEL",
        "CONFIRM_DECLINE_CANCEL",
    }
    assert expected == set(popup.BUTTON_MAP.keys())


def test_button_map_acknowledge_is_ok() -> None:
    """Verify the ACKNOWLEDGE button mapping."""
    assert popup.BUTTON_MAP["ACKNOWLEDGE"] == QMessageBox.StandardButton.Ok


def test_button_map_confirm_decline_includes_yes_and_no() -> None:
    """Verify the CONFIRM_DECLINE button mapping."""
    flags = popup.BUTTON_MAP["CONFIRM_DECLINE"]
    assert flags & QMessageBox.StandardButton.Yes
    assert flags & QMessageBox.StandardButton.No


# =============================================================================
# TESTS — DEFAULT_BUTTON
# =============================================================================


def test_default_button_keys_match_button_map() -> None:
    """Verify that DEFAULT_BUTTON keys match BUTTON_MAP."""
    assert set(popup.DEFAULT_BUTTON.keys()) == set(popup.BUTTON_MAP.keys())


def test_default_button_acknowledge_is_ok() -> None:
    """Verify the default button for ACKNOWLEDGE."""
    assert popup.DEFAULT_BUTTON["ACKNOWLEDGE"] == QMessageBox.StandardButton.Ok


def test_default_button_confirm_decline_is_yes() -> None:
    """Verify the default button for CONFIRM_DECLINE."""
    expected = QMessageBox.StandardButton.Yes
    assert popup.DEFAULT_BUTTON["CONFIRM_DECLINE"] == expected


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def mock_show(monkeypatch: pytest.MonkeyPatch) -> dict:
    """Mock popup.show to capture arguments and return Yes by default."""
    captured = {}

    def fake_show(
        title: str, text: str, icon: Any = None,
        buttons: Any = None, **kwargs: Any
    ) -> QMessageBox.StandardButton:
        """Mock implementation of popup.show."""
        captured["title"] = title
        captured["text"] = text
        captured["icon"] = icon
        captured["buttons"] = buttons
        return captured.get("return_value", QMessageBox.StandardButton.Yes)

    monkeypatch.setattr(popup, "show", fake_show)
    return captured


# =============================================================================
# TESTS — show_error/warning/info/question
# =============================================================================


def test_show_error_calls_show_with_critical(mock_show: dict) -> None:
    """Verify that show_error uses the CRITICAL icon."""
    popup.show_error("Oops", "Something failed")
    assert mock_show["icon"] == "CRITICAL"
    assert mock_show["title"] == "Oops"


def test_show_warning_calls_show_with_warning(mock_show: dict) -> None:
    """Verify that show_warning uses the WARNING icon."""
    popup.show_warning("Heads Up", "Mind this")
    assert mock_show["icon"] == "WARNING"


def test_show_info_calls_show_with_information(mock_show: dict) -> None:
    """Verify that show_info uses the INFORMATION icon."""
    popup.show_info("Note", "All good")
    assert mock_show["icon"] == "INFORMATION"


def test_show_question_uses_confirm_decline_by_default(
    mock_show: dict
) -> None:
    """Verify the default buttons for questions."""
    popup.show_question("Q", "Are you sure?")
    assert mock_show["buttons"] == "CONFIRM_DECLINE"


def test_show_question_uses_cancel_variant(mock_show: dict) -> None:
    """Verify the buttons for questions with a cancel option."""
    popup.show_question("Q", "Are you sure?", cancel_button=True)
    assert mock_show["buttons"] == "CONFIRM_DECLINE_CANCEL"


@pytest.mark.parametrize(
    "button_returned, expected_result",
    [
        (QMessageBox.StandardButton.Yes, True),
        (QMessageBox.StandardButton.No, False),
    ]
)
def test_show_question_returns_expected(
    mock_show: dict,
    button_returned: QMessageBox.StandardButton,
    expected_result: bool
) -> None:
    """Verify the return value of show_question."""
    mock_show["return_value"] = button_returned
    assert popup.show_question("Q", "Confirm?") is expected_result


# =============================================================================
# TEST EXECUTION
# =============================================================================

if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
