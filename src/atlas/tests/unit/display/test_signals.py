"""Atlas | Tests | Display | Signals.

Unit tests for display/signals.py.
Verifies signal definitions and emission behaviour.
"""

# =============================================================================
# IMPORTS
# =============================================================================

import sys

import pytest
from PyQt6.QtWidgets import QApplication

from atlas.display.signals import Signals

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def signals(qapp: QApplication) -> Signals:
    """Provide a fresh Signals instance for each test."""
    return Signals()


# =============================================================================
# TESTS — Signals
# =============================================================================


def test_signals_instantiates(signals: Signals) -> None:
    """Verify that signals can be instantiated."""
    assert signals is not None


def test_backup_started_emits(signals: Signals) -> None:
    """Verify the emission of the backup_started signal."""
    received = []
    signals.backup_started.connect(lambda: received.append(True))
    signals.backup_started.emit()
    assert received == [True]


def test_backup_finished_emits(signals: Signals) -> None:
    """Verify the emission of the backup_finished signal."""
    received = []
    signals.backup_finished.connect(lambda: received.append(True))
    signals.backup_finished.emit()
    assert received == [True]


def test_backup_cancelled_emits(signals: Signals) -> None:
    """Verify the emission of the backup_cancelled signal."""
    received = []
    signals.backup_cancelled.connect(lambda: received.append(True))
    signals.backup_cancelled.emit()
    assert received == [True]


def test_progress_emits_int_int(signals: Signals) -> None:
    """Verify the emission of the progress signal."""
    received = []
    signals.progress.connect(lambda a, b: received.append((a, b)))
    signals.progress.emit(3, 10)
    assert received == [(3, 10)]


def test_estimated_size_emits_string(signals: Signals) -> None:
    """Verify the emission of the estimated_size signal."""
    received = []
    signals.estimated_size.connect(lambda s: received.append(s))
    signals.estimated_size.emit("120 MB")
    assert received == ["120 MB"]


def test_scanned_entries_emits_string(signals: Signals) -> None:
    """Verify the emission of the scanned_entries signal."""
    received = []
    signals.scanned_entries.connect(lambda s: received.append(s))
    signals.scanned_entries.emit("Chrome / Profile 1")
    assert received == ["Chrome / Profile 1"]


def test_elapsed_time_emits_int(signals: Signals) -> None:
    """Verify the emission of the elapsed_time signal."""
    received = []
    signals.elapsed_time.connect(lambda t: received.append(t))
    signals.elapsed_time.emit(42)
    assert received == [42]


def test_disk_space_error_emits_two_strings(signals: Signals) -> None:
    """Verify the emission of the disk_space_error signal."""
    received = []
    signals.disk_space_error.connect(
        lambda req, avail: received.append((req, avail))
    )
    signals.disk_space_error.emit("5 GB", "1 GB")
    assert received == [("5 GB", "1 GB")]


def test_no_browsers_found_emits(signals: Signals) -> None:
    """Verify the emission of the no_browsers_found signal."""
    received = []
    signals.no_browsers_found.connect(lambda: received.append(True))
    signals.no_browsers_found.emit()
    assert received == [True]


# =============================================================================
# TEST EXECUTION
# =============================================================================

if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
