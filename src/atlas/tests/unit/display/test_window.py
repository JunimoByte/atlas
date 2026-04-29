"""Atlas | Tests | Display | Window.

Unit tests for display/window.py.
Covers UIMode enum, progress computation, elapsed time formatting,
and UI mode switching. The real UiDialog is used; no .ui files are loaded.
"""

# =============================================================================
# IMPORTS
# =============================================================================

import sys
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest
from PyQt6.QtWidgets import QApplication

from atlas.display.window import UIMode, Window

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def window(qapp: QApplication) -> Generator[Window, None, None]:
    """Provide a Window with controller and show_warning patched out."""
    with patch("atlas.display.window.Controller") as MockController:
        ctrl = MagicMock()
        MockController.return_value = ctrl
        win = Window()
    return win


# =============================================================================
# TESTS — UIMode Enum
# =============================================================================


def test_uimode_has_four_states() -> None:
    """Verify that UIMode defines exactly four display states."""
    expected = {UIMode.IDLE, UIMode.SCANNING, UIMode.COMPLETED, UIMode.ERROR}
    assert set(UIMode) == expected


@pytest.mark.parametrize(
    "mode, expected_value",
    [
        (UIMode.IDLE, "idle"),
        (UIMode.SCANNING, "scanning"),
        (UIMode.COMPLETED, "completed"),
        (UIMode.ERROR, "error"),
    ]
)
def test_uimode_values(mode: UIMode, expected_value: str) -> None:
    """Verify that UIMode states map to the expected string values."""
    assert isinstance(mode.value, str)
    assert mode.value == expected_value


# =============================================================================
# TESTS — UI_MODE_CONFIG
# =============================================================================


def test_ui_mode_config_covers_all_modes(window: Window) -> None:
    """Verify that UI_MODE_CONFIG covers all UIMode states."""
    assert set(Window.UI_MODE_CONFIG.keys()) == set(UIMode)


def test_ui_mode_config_entries_are_tuples(window: Window) -> None:
    """Verify that UI_MODE_CONFIG entries are tuples."""
    for value in Window.UI_MODE_CONFIG.values():
        assert isinstance(value, tuple)


# =============================================================================
# TESTS — Window initialisation
# =============================================================================


def test_window_has_interface(window: Window) -> None:
    """Verify that the window has an interface attribute."""
    assert hasattr(window, "interface")


def test_window_has_controller(window: Window) -> None:
    """Verify that the window has a controller attribute."""
    assert hasattr(window, "controller")


def test_window_has_signals(window: Window) -> None:
    """Verify that the window has a signals attribute."""
    assert hasattr(window, "signals")


def test_window_initial_formatted_size(window: Window) -> None:
    """Verify that formatted_size is initially empty."""
    assert window.formatted_size == ""


def test_window_initial_latest_scanned_info(window: Window) -> None:
    """Verify that latest_scanned_info is initially empty."""
    assert window.latest_scanned_info == ""


# =============================================================================
# TESTS — Update Progress
# =============================================================================


@pytest.mark.parametrize(
    "current, total, expected, initial_val",
    [
        (5, 10, 50, 0),
        (10, 10, 100, 0),
        (200, 10, 100, 0),
        (0, 10, 0, 0),
        (5, 0, 42, 42),
        (5, -1, 42, 42),
    ]
)
def test_update_progress_states(
    window: Window, current: int, total: int, expected: int, initial_val: int
) -> None:
    """Verify progress calculation and value clamping."""
    window.interface.progress_bar.setValue(initial_val)
    window._update_progress(current, total)
    assert window.interface.progress_bar.value() == expected


# =============================================================================
# TESTS — Update Elapsed Time
# =============================================================================


def test_update_elapsed_time_sets_label(window: Window) -> None:
    """Verify that the elapsed time label is updated."""
    window._update_elapsed_time(90)
    text = window.interface.time_elapsed.text()
    assert "1m" in text and "30s" in text


def test_update_elapsed_time_uses_formatted_size_as_info(
    window: Window
) -> None:
    """Verify that the formatted size is included in the time label."""
    window.formatted_size = "120 MB"
    window._update_elapsed_time(30)
    assert "120 MB" in window.interface.time_elapsed.text()


def test_update_elapsed_time_uses_scanned_info_when_no_size(
    window: Window
) -> None:
    """Verify the fallback to scanned info in the time label."""
    window.formatted_size = ""
    window.latest_scanned_info = "Chrome / Default"
    window._update_elapsed_time(30)
    assert "Chrome / Default" in window.interface.time_elapsed.text()


def test_update_elapsed_time_skips_duplicate_update(window: Window) -> None:
    """Verify that redundant label updates are skipped."""
    window._update_elapsed_time(30)

    # use a sentinel to see if setText is called again
    call_count = []
    original_set = window.interface.time_elapsed.setText

    def wrap_set(t: str) -> None:
        """Wrap setText to track calls."""
        call_count.append(t)
        original_set(t)

    window.interface.time_elapsed.setText = wrap_set

    window._update_elapsed_time(30)
    assert call_count == []  # No re-render for identical text


# =============================================================================
# TESTS — Set UI Mode
# =============================================================================


def test_idle_mode_shows_description(window: Window) -> None:
    """Verify UI visibility in IDLE mode."""
    window._set_ui_mode(UIMode.IDLE)
    assert not window.interface.description.isHidden()


def test_idle_mode_hides_progress_bar(window: Window) -> None:
    """Verify that the progress bar is hidden in IDLE mode."""
    window._set_ui_mode(UIMode.IDLE)
    assert window.interface.progress_bar.isHidden()


# =============================================================================
# TESTS — Scanning Mode
# =============================================================================


def test_scanning_mode_shows_progress_bar(window: Window) -> None:
    """Verify UI visibility in SCANNING mode."""
    window._set_ui_mode(UIMode.SCANNING)
    assert not window.interface.progress_bar.isHidden()


def test_scanning_mode_hides_description(window: Window) -> None:
    """Verify that the description is hidden in SCANNING mode."""
    window._set_ui_mode(UIMode.SCANNING)
    assert window.interface.description.isHidden()


def test_scanning_mode_resets_progress_bar(window: Window) -> None:
    """Verify that the progress bar is reset in SCANNING mode."""
    window.interface.progress_bar.setValue(75)
    window._set_ui_mode(UIMode.SCANNING)
    assert window.interface.progress_bar.value() == 0


# =============================================================================
# TESTS — Completed Mode
# =============================================================================


def test_completed_mode_shows_completed_description(window: Window) -> None:
    """Verify UI visibility in COMPLETED mode."""
    window._set_ui_mode(UIMode.COMPLETED)
    assert not window.interface.completed_description.isHidden()


def test_completed_mode_hides_progress_bar(window: Window) -> None:
    """Verify that the progress bar is hidden in COMPLETED mode."""
    window._set_ui_mode(UIMode.COMPLETED)
    assert window.interface.progress_bar.isHidden()


# =============================================================================
# TESTS — Error Mode
# =============================================================================


def test_error_mode_shows_cancel_description(window: Window) -> None:
    """Verify UI visibility in ERROR mode."""
    window._set_ui_mode(UIMode.ERROR)
    assert not window.interface.cancel_description.isHidden()


def test_error_mode_sets_custom_text(window: Window) -> None:
    """Verify that the error text is displayed in ERROR mode."""
    window._set_ui_mode(UIMode.ERROR, error_text="Disk full.")
    assert window.interface.cancel_description.text() == "Disk full."


def test_error_mode_without_text_does_not_overwrite_label(
    window: Window
) -> None:
    """Verify that the error label is preserved if no text is provided."""
    window.interface.cancel_description.setText("Original")
    window._set_ui_mode(UIMode.ERROR)
    assert window.interface.cancel_description.text() == "Original"


# =============================================================================
# TESTS — Scan, Complete, and _on_backup_started
# =============================================================================


def test_scan_delegates_to_controller(window: Window) -> None:
    """Verify that scan() initiates a backup."""
    window.scan()
    window.controller.start_backup.assert_called_once()


def test_on_backup_started_switches_to_scanning(window: Window) -> None:
    """Verify the UI transition when the backup starts."""
    window._on_backup_started()
    assert not window.interface.progress_bar.isHidden()
    assert window.interface.description.isHidden()


def test_complete_switches_to_completed(window: Window) -> None:
    """Verify the UI transition when the backup completes."""
    window.complete()
    assert not window.interface.completed_description.isHidden()


# =============================================================================
# TESTS — Signals
# =============================================================================


def test_estimated_size_signal_updates_attribute(window: Window) -> None:
    """Verify that the estimated size signal updates the window attribute."""
    window.signals.estimated_size.emit("256 MB")
    assert window.formatted_size == "256 MB"


def test_scanned_entries_signal_updates_attribute(window: Window) -> None:
    """Verify that the scanned entries signal updates the window attribute."""
    window.signals.scanned_entries.emit("Firefox / default")
    assert window.latest_scanned_info == "Firefox / default"


# =============================================================================
# TEST EXECUTION
# =============================================================================

if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
