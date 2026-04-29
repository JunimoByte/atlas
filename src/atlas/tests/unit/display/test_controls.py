"""Atlas | Tests | Display | Controls.

Unit tests for display/controls.py.
Covers elapsed time formatting and button configuration helpers.
"""

# =============================================================================
# IMPORTS
# =============================================================================

import sys

import pytest
from PyQt6.QtWidgets import QAbstractButton, QApplication, QDialogButtonBox

from atlas.display import controls

# =============================================================================
# TESTS — Format elapsed time
# =============================================================================


@pytest.mark.parametrize(
    "seconds, expected",
    [
        (45, "Time Elapsed: 45s"),
        (90, "Time Elapsed: 1m 30s"),
        (3661, "Time Elapsed: 1h 1m 1s"),
        (0, "Time Elapsed: 0s"),
        (60, "Time Elapsed: 1m 0s"),
        (3600, "Time Elapsed: 1h 0m 0s"),
    ],
)
def test_format_elapsed_time_variations(seconds: int, expected: str) -> None:
    """Verify elapsed time formatting for various inputs."""
    result = controls.format_elapsed_time(seconds)
    assert result == expected


def test_format_elapsed_time_with_info() -> None:
    """Verify that the info string is appended in parentheses."""
    result = controls.format_elapsed_time(30, info="Scanning...")
    assert result == "Time Elapsed: 30s (Scanning...)"


def test_format_elapsed_time_without_info_no_parens() -> None:
    """Verify that parentheses are omitted if the info string is empty."""
    result = controls.format_elapsed_time(30, info="")
    assert "(" not in result


# =============================================================================
# TESTS — Get button
# =============================================================================


def test_get_button_returns_none_for_invalid_name(qapp: QApplication) -> None:
    """Verify that None is returned for unknown button names."""
    box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
    result = controls._get_button(box, "NotAButton")
    assert result is None


def test_get_button_returns_button_for_valid_name(qapp: QApplication) -> None:
    """Verify that a button is returned for valid names."""
    box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
    result = controls._get_button(box, "Ok")
    assert isinstance(result, QAbstractButton)


# =============================================================================
# TESTS — Set text
# =============================================================================


def test_set_text_updates_button_label(qapp: QApplication) -> None:
    """Verify that set_text updates the button label."""
    box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
    controls.set_text(box, "Ok", "Backup")
    button = controls._get_button(box, "Ok")
    assert button.text() == "Backup"


def test_set_text_does_nothing_for_missing_button(qapp: QApplication) -> None:
    """Verify that set_text handles missing buttons gracefully."""
    box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
    controls.set_text(box, "Ghost", "Irrelevant")  # shouldn't crash


# =============================================================================
# TESTS — Set button visible
# =============================================================================


def test_set_button_visible_hides_button(qapp: QApplication) -> None:
    """Verify that buttons can be hidden."""
    box = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
    controls.set_button_visible(box, "Cancel", False)
    button = controls._get_button(box, "Cancel")
    assert not button.isVisible()


def test_set_button_visible_shows_button(qapp: QApplication) -> None:
    """Verify that buttons can be shown."""
    box = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
    controls.set_button_visible(box, "Cancel", False)
    controls.set_button_visible(box, "Cancel", True)
    button = controls._get_button(box, "Cancel")
    assert not button.isHidden()


# =============================================================================
# TESTS — Set connection
# =============================================================================


def test_set_connection_ignores_invalid_signal_name(
    qapp: QApplication
) -> None:
    """Verify that unknown signals are ignored."""
    box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
    controls.set_connection(box, "clicked", lambda: None)  # shouldn't crash


def test_set_connection_ignores_non_callable(qapp: QApplication) -> None:
    """Verify that non-callable commands are ignored."""
    box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
    controls.set_connection(
        box, "accepted", "not_a_callable"
    )  # shouldn't crash


def test_set_connection_connects_accepted_signal(qapp: QApplication) -> None:
    """Verify that the accepted signal can be wired."""
    box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
    called = []
    controls.set_connection(box, "accepted", lambda: called.append(True))
    box.accepted.emit()
    assert called


# =============================================================================
# TESTS — Configure button
# =============================================================================


def test_configure_button_applies_visibility_and_text(
    qapp: QApplication
) -> None:
    """Verify button configuration for visibility and text."""
    box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
    controls.configure_button(box, "Ok", {"visible": True, "text": "Go"})
    button = controls._get_button(box, "Ok")
    assert not button.isHidden()
    assert button.text() == "Go"


def test_configure_button_hides_button_without_text(
    qapp: QApplication
) -> None:
    """Verify that buttons are hidden when specified."""
    box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
    controls.configure_button(box, "Ok", {"visible": False})
    button = controls._get_button(box, "Ok")
    assert not button.isVisible()


# =============================================================================
# TEST EXECUTION
# =============================================================================

if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
