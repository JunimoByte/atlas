"""Atlas | Tests | Display | Conftest.

Shared pytest fixtures for display unit tests.
Provides a session-scoped QApplication instance required by all
Qt widget tests.
"""

# =============================================================================
# IMPORTS
# =============================================================================

import sys
from typing import Generator

import pytest
from atlas.compatibility.qt import QtWidgets

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture(scope="session")
def qapp() -> Generator[QtWidgets.QApplication, None, None]:
    """Provide a session-scoped QtWidgets.QApplication instance.

    Qt requires exactly one QtWidgets.QApplication to exist for the
    lifetime of any test that creates widgets or uses signals.
    A single instance is created for the entire test session
    and reused across all tests to avoid repeated initialisation
    overhead.
    """
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication(sys.argv[:1])
    yield app
