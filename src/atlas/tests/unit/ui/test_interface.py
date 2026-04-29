"""Unit tests for the UiDialog class in atlas.ui.interface.

Verifies that setup_ui correctly creates and exposes all required widget
attributes on the dialog.
"""

# =============================================================================
# IMPORTS
# =============================================================================

import sys
from typing import Generator

import pytest
from PyQt6.QtWidgets import QApplication, QWidget

from atlas.ui.interface import UiDialog

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture(scope="session")
def app() -> Generator[QApplication, None, None]:
    """Provide session-scoped QApplication instance for Qt widgets."""
    app_instance = QApplication.instance()
    if app_instance is None:
        app_instance = QApplication([])
    return app_instance


@pytest.fixture
def ui_dialog(app: QApplication) -> UiDialog:
    """Provide a fresh UiDialog instance for each test."""
    return UiDialog()


@pytest.fixture
def mock_window(app: QApplication) -> QWidget:
    """Provide a real QWidget to act as parent for UI creation."""
    return QWidget()


# =============================================================================
# TESTS
# =============================================================================


def test_setup_ui_creates_all_elements(
    ui_dialog: UiDialog, mock_window: QWidget
) -> None:
    """setup_ui should create all expected widget attributes on dialog.

    Checks that every label, button box, progress bar, and backdrop
    element is present and accessible after calling setup_ui.
    """
    ui_dialog.setup_ui(mock_window)

    required_attributes = [
        "title",
        "description",
        "progress_description",
        "completed_description",
        "cancel_description",
        "time_elapsed",
        "selection",
        "progress_bar",
        "backdrop",
    ]

    for attr in required_attributes:
        assert hasattr(ui_dialog, attr), f"UiDialog missing attribute: {attr}"

    assert ui_dialog.backdrop.objectName() == "Backdrop"


# =============================================================================
# TEST EXECUTION
# =============================================================================

if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
