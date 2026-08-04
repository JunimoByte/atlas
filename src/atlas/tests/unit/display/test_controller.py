"""Atlas | Tests | Display | Controller.

Unit tests for display/controller.py.
Covers state management, signal routing, and timer behaviour.
Worker threads are patched to prevent real I/O in unit tests.
"""

import sys
import time
from unittest.mock import patch

import pytest

from atlas.compatibility.qt import QtCore, QtWidgets
from atlas.display.controller import (
    THREAD_WAIT_TIMEOUT_MS,
    UPDATE_INTERVAL_MS,
    Controller,
    ControllerState,
)
from atlas.display.signals import Signals


@pytest.fixture
def signals(qapp: QtWidgets.QApplication) -> Signals:
    """Provide a Signals instance for unit testing."""
    return Signals()


@pytest.fixture
def ctrl(signals: Signals) -> Controller:
    """Provide a Controller instance initialized with test signals."""
    return Controller(signals)


def test_controller_initial_state(ctrl: Controller) -> None:
    """Verify that Controller initializes in IDLE state with default members."""
    assert ctrl.worker is None
    assert ctrl._worker_thread is None
    assert isinstance(ctrl.elapsed_timer, QtCore.QTimer)
    assert ctrl.state == ControllerState.IDLE


def test_controller_holds_signals_reference(
    ctrl: Controller, signals: Signals
) -> None:
    """Verify that Controller stores the provided Signals reference."""
    assert ctrl.signals is signals


def test_start_backup_sets_active_flag(ctrl: Controller) -> None:
    """Verify that start_backup transitions state to RUNNING."""
    with patch.object(ctrl, "_deploy_worker"), \
         patch.object(ctrl, "_start_elapsed_timer"):
        ctrl.start_backup()
    assert ctrl.state == ControllerState.RUNNING


def test_start_backup_emits_backup_started(
    ctrl: Controller, signals: Signals
) -> None:
    """Verify that start_backup emits the backup_started signal."""
    received = []
    signals.backup_started.connect(lambda: received.append(True))
    with patch.object(ctrl, "_deploy_worker"), \
         patch.object(ctrl, "_start_elapsed_timer"):
        ctrl.start_backup()
    assert received == [True]


def test_start_backup_is_idempotent(
    ctrl: Controller, signals: Signals
) -> None:
    """Verify that repeated start_backup calls do not re-trigger setup."""
    started = []
    signals.backup_started.connect(lambda: started.append(True))
    with patch.object(ctrl, "_deploy_worker"), \
         patch.object(ctrl, "_start_elapsed_timer"):
        ctrl.start_backup()
        ctrl.start_backup()
    assert len(started) == 1


def test_start_backup_resets_on_deploy_error(
    ctrl: Controller, signals: Signals
) -> None:
    """Verify state resets to FAILED if worker deployment fails."""
    finished = []
    signals.worker_error.connect(lambda msg: finished.append(msg))
    with patch.object(ctrl, "_start_elapsed_timer"):
        with patch.object(
            ctrl, "_deploy_worker", side_effect=RuntimeError("fail")
        ):
            with patch.object(ctrl, "_request_worker_shutdown"):
                ctrl.start_backup()
    assert ctrl.state == ControllerState.FAILED
    assert finished == ["Failed to initialize the backup process."]


def test_cancel_backup_sets_cancelling_flag(ctrl: Controller) -> None:
    """Verify that cancel_backup transitions state to CANCELLING."""
    ctrl.state = ControllerState.RUNNING
    with patch.object(ctrl, "_stop_elapsed_timer"), \
         patch.object(ctrl, "_request_worker_shutdown"):
        ctrl.cancel_backup()
    assert ctrl.state == ControllerState.CANCELLING


def test_cancel_backup_is_noop_when_inactive(
    ctrl: Controller, signals: Signals
) -> None:
    """Verify cancel_backup does nothing when state is not RUNNING."""
    cancelled = []
    signals.backup_cancelled.connect(lambda: cancelled.append(True))
    ctrl.cancel_backup()
    assert cancelled == []


def test_handle_thread_finished_after_cancellation(
    ctrl: Controller, signals: Signals
) -> None:
    """Verify thread completion after cancellation resets state to IDLE."""
    ctrl.state = ControllerState.CANCELLING
    received = []
    signals.backup_cancelled.connect(lambda: received.append(True))
    ctrl._handle_thread_finished()
    assert ctrl.state == ControllerState.IDLE
    assert received == [True]


def test_handle_thread_finished_after_completion(
    ctrl: Controller, signals: Signals
) -> None:
    """Verify thread completion after success resets state to IDLE."""
    ctrl.state = ControllerState.SUCCESS
    received = []
    signals.backup_finished.connect(lambda: received.append(True))
    ctrl._handle_thread_finished()
    assert ctrl.state == ControllerState.IDLE
    assert received == [True]


def test_handle_thread_finished_unexpected(
    ctrl: Controller, signals: Signals
) -> None:
    """Verify unexpected thread exit sets state to FAILED."""
    ctrl.state = ControllerState.RUNNING
    received = []
    signals.worker_error.connect(lambda x: received.append(x))
    with patch.object(ctrl, "_stop_elapsed_timer"):
        ctrl._handle_thread_finished()
    assert ctrl.state == ControllerState.FAILED
    assert received == ["The backup process experienced an unexpected error."]


def test_cleanup_calls_stop_elapsed_timer(ctrl: Controller) -> None:
    """Verify cleanup stops the elapsed timer."""
    with patch.object(ctrl, "_stop_elapsed_timer") as mock_stop, \
         patch.object(ctrl, "_request_worker_shutdown"):
        ctrl.cleanup()
    mock_stop.assert_called_once()


def test_cleanup_calls_request_worker_shutdown_when_active(
    ctrl: Controller
) -> None:
    """Verify cleanup requests worker shutdown when backup is active."""
    ctrl.state = ControllerState.RUNNING
    with patch.object(ctrl, "_stop_elapsed_timer"), \
         patch.object(ctrl, "_request_worker_shutdown") as mock_cleanup:
        ctrl.cleanup()
    mock_cleanup.assert_called_once()


def test_cleanup_skips_worker_when_inactive(ctrl: Controller) -> None:
    """Verify cleanup skips worker shutdown when backup is inactive."""
    with patch.object(ctrl, "_stop_elapsed_timer"), \
         patch.object(ctrl, "_request_worker_shutdown") as mock_cleanup:
        ctrl.cleanup()
    mock_cleanup.assert_not_called()


def test_handle_worker_completion_sets_success(ctrl: Controller) -> None:
    """Verify worker completion updates state to SUCCESS."""
    ctrl.state = ControllerState.RUNNING
    with patch.object(ctrl, "_stop_elapsed_timer"), \
         patch.object(ctrl, "_request_worker_shutdown"):
        ctrl._handle_worker_completion()
    assert ctrl.state == ControllerState.SUCCESS


def test_handle_worker_failure_sets_failed_state(ctrl: Controller) -> None:
    """Verify worker failure updates state to FAILED."""
    ctrl.state = ControllerState.RUNNING
    with patch.object(ctrl, "_stop_elapsed_timer"), \
         patch.object(ctrl, "_request_worker_shutdown"):
        ctrl._handle_worker_failure("boom")
    assert ctrl.state == ControllerState.FAILED


def test_handle_worker_failure_emits_signal(
    ctrl: Controller, signals: Signals
) -> None:
    """Verify worker failure emits worker_error signal."""
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
    """Verify worker failure is ignored if cancellation is in progress."""
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


def test_handle_disk_space_error_emits_signal(
    ctrl: Controller, signals: Signals
) -> None:
    """Verify disk space error emits disk_space_error signal."""
    ctrl.state = ControllerState.RUNNING
    received = []
    signals.disk_space_error.connect(lambda r, a: received.append((r, a)))
    with patch.object(ctrl, "_stop_elapsed_timer"), \
         patch.object(ctrl, "_request_worker_shutdown"):
        ctrl._handle_disk_space_error("5 GB", "1 GB")
    assert received == [("5 GB", "1 GB")]


def test_handle_disk_space_error_sets_blocked_state(
    ctrl: Controller
) -> None:
    """Verify disk space error sets state to BLOCKED."""
    ctrl.state = ControllerState.RUNNING
    with patch.object(ctrl, "_stop_elapsed_timer"), \
         patch.object(ctrl, "_request_worker_shutdown"):
        ctrl._handle_disk_space_error("5 GB", "1 GB")
    assert ctrl.state == ControllerState.BLOCKED


def test_handle_no_browsers_emits_signal(
    ctrl: Controller, signals: Signals
) -> None:
    """Verify no browsers error emits no_browsers_found signal."""
    ctrl.state = ControllerState.RUNNING
    received = []
    signals.no_browsers_found.connect(lambda: received.append(True))
    with patch.object(ctrl, "_stop_elapsed_timer"), \
         patch.object(ctrl, "_request_worker_shutdown"):
        ctrl._handle_no_browsers()
    assert received == [True]


def test_handle_no_browsers_sets_empty_state(ctrl: Controller) -> None:
    """Verify no browsers error sets state to EMPTY."""
    ctrl.state = ControllerState.RUNNING
    with patch.object(ctrl, "_stop_elapsed_timer"), \
         patch.object(ctrl, "_request_worker_shutdown"):
        ctrl._handle_no_browsers()
    assert ctrl.state == ControllerState.EMPTY


def test_tick_emits_elapsed_time(
    ctrl: Controller, signals: Signals
) -> None:
    """Verify timer tick emits elapsed_time signal."""
    ctrl.state = ControllerState.RUNNING
    ctrl.elapsed_start_time = time.monotonic() - 5.0
    received = []
    signals.elapsed_time.connect(lambda t: received.append(t))
    ctrl._tick()
    assert received and received[0] >= 5


def test_tick_is_noop_when_inactive(
    ctrl: Controller, signals: Signals
) -> None:
    """Verify timer tick does nothing when state is IDLE."""
    ctrl.state = ControllerState.IDLE
    received = []
    signals.elapsed_time.connect(lambda t: received.append(t))
    ctrl._tick()
    assert received == []


def test_thread_wait_timeout_is_positive() -> None:
    """Verify THREAD_WAIT_TIMEOUT_MS constant is positive integer."""
    assert isinstance(THREAD_WAIT_TIMEOUT_MS, int)
    assert THREAD_WAIT_TIMEOUT_MS > 0


def test_update_interval_is_positive() -> None:
    """Verify UPDATE_INTERVAL_MS constant is positive integer."""
    assert isinstance(UPDATE_INTERVAL_MS, int)
    assert UPDATE_INTERVAL_MS > 0


def test_invalid_state_transition_rejected(ctrl: Controller) -> None:
    """Verify invalid FSM transition returns False and preserves state."""
    ctrl.state = ControllerState.IDLE
    result = ctrl._set_state(ControllerState.SUCCESS)
    assert result is False
    assert ctrl.state == ControllerState.IDLE


def test_reset_clears_failed_state(ctrl: Controller) -> None:
    """Verify reset transitions FAILED state back to IDLE."""
    ctrl.state = ControllerState.FAILED
    ctrl.reset()
    assert ctrl.state == ControllerState.IDLE


def test_reset_noop_when_not_failed(ctrl: Controller) -> None:
    """Verify reset has no effect when state is not FAILED."""
    ctrl.state = ControllerState.RUNNING
    ctrl.reset()
    assert ctrl.state == ControllerState.RUNNING


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
