"""Atlas | Tests | Display | Controller.

Unit tests for display/controller.py.
Covers state management, signal routing, and timer behaviour.
Worker threads are patched to prevent real I/O in unit tests.
"""

import sys
import time
from unittest.mock import patch

import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

from atlas.display.controller import (
    THREAD_WAIT_TIMEOUT_MS,
    UPDATE_INTERVAL_MS,
    Controller,
    ControllerState,
)
from atlas.display.signals import Signals

@pytest.fixture
def signals(qapp: QApplication) -> Signals:
    return Signals()

@pytest.fixture
def ctrl(signals: Signals) -> Controller:
    return Controller(signals)


def test_controller_initial_state(ctrl: Controller) -> None:
    assert ctrl.worker is None
    assert ctrl._worker_thread is None
    assert isinstance(ctrl.elapsed_timer, QTimer)
    assert ctrl.state == ControllerState.IDLE

def test_controller_holds_signals_reference(ctrl: Controller, signals: Signals) -> None:
    assert ctrl.signals is signals

def test_start_backup_sets_active_flag(ctrl: Controller) -> None:
    with patch.object(ctrl, "_deploy_worker"), \
         patch.object(ctrl, "_start_elapsed_timer"):
        ctrl.start_backup()
    assert ctrl.state == ControllerState.RUNNING

def test_start_backup_emits_backup_started(ctrl: Controller, signals: Signals) -> None:
    received = []
    signals.backup_started.connect(lambda: received.append(True))
    with patch.object(ctrl, "_deploy_worker"), \
         patch.object(ctrl, "_start_elapsed_timer"):
        ctrl.start_backup()
    assert received == [True]

def test_start_backup_is_idempotent(ctrl: Controller, signals: Signals) -> None:
    started = []
    signals.backup_started.connect(lambda: started.append(True))
    with patch.object(ctrl, "_deploy_worker"), \
         patch.object(ctrl, "_start_elapsed_timer"):
        ctrl.start_backup()
        ctrl.start_backup()
    assert len(started) == 1

def test_start_backup_resets_on_deploy_error(ctrl: Controller, signals: Signals) -> None:
    finished = []
    signals.worker_error.connect(lambda msg: finished.append(msg))
    with patch.object(ctrl, "_start_elapsed_timer"):
        with patch.object(ctrl, "_deploy_worker", side_effect=RuntimeError("fail")):
            with patch.object(ctrl, "_request_worker_shutdown"):
                ctrl.start_backup()
    assert ctrl.state == ControllerState.FAILED
    assert finished == ["Failed to initialize the backup process."]

def test_cancel_backup_sets_cancelling_flag(ctrl: Controller) -> None:
    ctrl.state = ControllerState.RUNNING
    with patch.object(ctrl, "_stop_elapsed_timer"), \
         patch.object(ctrl, "_request_worker_shutdown"):
        ctrl.cancel_backup()
    assert ctrl.state == ControllerState.CANCELLING

def test_cancel_backup_is_noop_when_inactive(ctrl: Controller, signals: Signals) -> None:
    cancelled = []
    signals.backup_cancelled.connect(lambda: cancelled.append(True))
    ctrl.cancel_backup()
    assert cancelled == []

def test_handle_thread_finished_after_cancellation(ctrl: Controller, signals: Signals) -> None:
    ctrl.state = ControllerState.CANCELLING
    received = []
    signals.backup_cancelled.connect(lambda: received.append(True))
    ctrl._handle_thread_finished()
    assert ctrl.state == ControllerState.IDLE
    assert received == [True]

def test_handle_thread_finished_after_completion(ctrl: Controller, signals: Signals) -> None:
    ctrl.state = ControllerState.SUCCESS
    received = []
    signals.backup_finished.connect(lambda: received.append(True))
    ctrl._handle_thread_finished()
    assert ctrl.state == ControllerState.IDLE
    assert received == [True]

def test_handle_thread_finished_unexpected(ctrl: Controller, signals: Signals) -> None:
    ctrl.state = ControllerState.RUNNING
    received = []
    signals.worker_error.connect(lambda x: received.append(x))
    with patch.object(ctrl, "_stop_elapsed_timer"):
        ctrl._handle_thread_finished()
    assert ctrl.state == ControllerState.FAILED
    assert received == ["The backup process experienced an unexpected error."]

def test_cleanup_calls_stop_elapsed_timer(ctrl: Controller) -> None:
    with patch.object(ctrl, "_stop_elapsed_timer") as mock_stop, \
         patch.object(ctrl, "_request_worker_shutdown"):
        ctrl.cleanup()
    mock_stop.assert_called_once()

def test_cleanup_calls_request_worker_shutdown_when_active(ctrl: Controller) -> None:
    ctrl.state = ControllerState.RUNNING
    with patch.object(ctrl, "_stop_elapsed_timer"), \
         patch.object(ctrl, "_request_worker_shutdown") as mock_cleanup:
        ctrl.cleanup()
    mock_cleanup.assert_called_once()

def test_cleanup_skips_worker_when_inactive(ctrl: Controller) -> None:
    with patch.object(ctrl, "_stop_elapsed_timer"), \
         patch.object(ctrl, "_request_worker_shutdown") as mock_cleanup:
        ctrl.cleanup()
    mock_cleanup.assert_not_called()

def test_handle_worker_completion_sets_success(ctrl: Controller) -> None:
    ctrl.state = ControllerState.RUNNING
    with patch.object(ctrl, "_stop_elapsed_timer"), \
         patch.object(ctrl, "_request_worker_shutdown"):
        ctrl._handle_worker_completion()
    assert ctrl.state == ControllerState.SUCCESS


def test_handle_worker_failure_sets_failed_state(ctrl: Controller) -> None:
    ctrl.state = ControllerState.RUNNING
    with patch.object(ctrl, "_stop_elapsed_timer"), \
         patch.object(ctrl, "_request_worker_shutdown"):
        ctrl._handle_worker_failure("boom")
    assert ctrl.state == ControllerState.FAILED


def test_handle_worker_failure_emits_signal(
    ctrl: Controller, signals: Signals
) -> None:
    ctrl.state = ControllerState.RUNNING
    received = []
    signals.worker_error.connect(lambda message: received.append(message))
    with patch.object(ctrl, "_stop_elapsed_timer"), \
         patch.object(ctrl, "_request_worker_shutdown"):
        ctrl._handle_worker_failure("boom")
    assert received == ["boom"]


def test_handle_worker_failure_ignored_while_cancelling(
    ctrl: Controller, signals: Signals
) -> None:
    ctrl.state = ControllerState.CANCELLING
    received = []
    signals.worker_error.connect(lambda message: received.append(message))
    with patch.object(ctrl, "_stop_elapsed_timer") as mock_stop, \
         patch.object(ctrl, "_request_worker_shutdown") as mock_shutdown:
        ctrl._handle_worker_failure("boom")
    mock_stop.assert_not_called()
    mock_shutdown.assert_not_called()
    assert received == []
    assert ctrl.state == ControllerState.CANCELLING

def test_handle_disk_space_error_emits_signal(ctrl: Controller, signals: Signals) -> None:
    ctrl.state = ControllerState.RUNNING
    received = []
    signals.disk_space_error.connect(lambda r, a: received.append((r, a)))
    with patch.object(ctrl, "_stop_elapsed_timer"), \
         patch.object(ctrl, "_request_worker_shutdown"):
        ctrl._handle_disk_space_error("5 GB", "1 GB")
    assert received == [("5 GB", "1 GB")]

def test_handle_disk_space_error_sets_blocked_state(ctrl: Controller) -> None:
    ctrl.state = ControllerState.RUNNING
    with patch.object(ctrl, "_stop_elapsed_timer"), \
         patch.object(ctrl, "_request_worker_shutdown"):
        ctrl._handle_disk_space_error("5 GB", "1 GB")
    assert ctrl.state == ControllerState.BLOCKED

def test_handle_no_browsers_emits_signal(ctrl: Controller, signals: Signals) -> None:
    ctrl.state = ControllerState.RUNNING
    received = []
    signals.no_browsers_found.connect(lambda: received.append(True))
    with patch.object(ctrl, "_stop_elapsed_timer"), \
         patch.object(ctrl, "_request_worker_shutdown"):
        ctrl._handle_no_browsers()
    assert received == [True]

def test_handle_no_browsers_sets_empty_state(ctrl: Controller) -> None:
    ctrl.state = ControllerState.RUNNING
    with patch.object(ctrl, "_stop_elapsed_timer"), \
         patch.object(ctrl, "_request_worker_shutdown"):
        ctrl._handle_no_browsers()
    assert ctrl.state == ControllerState.EMPTY

def test_tick_emits_elapsed_time(ctrl: Controller, signals: Signals) -> None:
    ctrl.state = ControllerState.RUNNING
    ctrl.elapsed_start_time = time.monotonic() - 5.0
    received = []
    signals.elapsed_time.connect(lambda t: received.append(t))
    ctrl._tick()
    assert received and received[0] >= 5

def test_tick_is_noop_when_inactive(ctrl: Controller, signals: Signals) -> None:
    ctrl.state = ControllerState.IDLE
    received = []
    signals.elapsed_time.connect(lambda t: received.append(t))
    ctrl._tick()
    assert received == []

def test_thread_wait_timeout_is_positive() -> None:
    assert isinstance(THREAD_WAIT_TIMEOUT_MS, int)
    assert THREAD_WAIT_TIMEOUT_MS > 0

def test_update_interval_is_positive() -> None:
    assert isinstance(UPDATE_INTERVAL_MS, int)
    assert UPDATE_INTERVAL_MS > 0

def test_invalid_state_transition_rejected(ctrl: Controller) -> None:
    ctrl.state = ControllerState.IDLE
    result = ctrl._set_state(ControllerState.SUCCESS)
    assert result is False
    assert ctrl.state == ControllerState.IDLE

def test_reset_clears_failed_state(ctrl: Controller) -> None:
    ctrl.state = ControllerState.FAILED
    ctrl.reset()
    assert ctrl.state == ControllerState.IDLE

def test_reset_noop_when_not_failed(ctrl: Controller) -> None:
    ctrl.state = ControllerState.RUNNING
    ctrl.reset()
    assert ctrl.state == ControllerState.RUNNING

if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
