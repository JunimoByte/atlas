"""Atlas | Display | Controller.

Handles application logic, worker lifecycle, and state management.
Separates execution logic from the UI.
"""

# =============================================================================
# IMPORTS
# =============================================================================

import logging
import time
from enum import Enum, auto
from typing import Optional

from PyQt6.QtCore import QObject, QThread, QTimer

from atlas.backup import worker as Backup
from atlas.display.signals import Signals

# =============================================================================
# LOGGING
# =============================================================================

LOGGER = logging.getLogger(__name__)

# =============================================================================
# CONSTANTS
# =============================================================================

THREAD_WAIT_TIMEOUT_MS = 2000
"""Timeout in milliseconds for worker thread shutdown."""

UPDATE_INTERVAL_MS = 300
"""Interval in milliseconds for elapsed time timer updates."""

SECONDS_PER_HOUR = 3600
"""Number of seconds in one hour for elapsed time calculations."""

SECONDS_PER_MINUTE = 60
"""Number of seconds in one minute for elapsed time calculations."""

# =============================================================================
# CLASSES
# =============================================================================


class ControllerState(Enum):
    """Machine state for the controller to track workflow lifecycle."""

    IDLE       = auto()  # waiting for user action
    RUNNING    = auto()  # pipeline active
    SUCCESS    = auto()  # backup completed fully
    EMPTY      = auto()  # no browsers found, valid no-op
    BLOCKED    = auto()  # cannot proceed (disk full, permissions)
    CANCELLING = auto()  # user-requested stop
    FAILED     = auto()  # crash, hang, or unhandled exception only


VALID_TRANSITIONS = {
    ControllerState.IDLE:       {ControllerState.RUNNING},
    ControllerState.RUNNING:    {
        ControllerState.SUCCESS,
        ControllerState.EMPTY,
        ControllerState.BLOCKED,
        ControllerState.CANCELLING,
        ControllerState.FAILED,
    },
    ControllerState.SUCCESS:    {ControllerState.IDLE},
    ControllerState.EMPTY:      {ControllerState.IDLE},
    ControllerState.BLOCKED:    {ControllerState.IDLE},
    ControllerState.CANCELLING: {ControllerState.IDLE, ControllerState.FAILED},
    ControllerState.FAILED:     {ControllerState.IDLE},
}


class Controller(QObject):
    """Control the backup workflow and manage the worker thread.

    Responsibilities:
    - Manage QThread and Worker lifecycle
    - Route signals from Worker to Signals correctly
    - Track elapsed time
    - Maintain an airtight finite state machine
    """

    def __init__(self, signals: Signals) -> None:
        """Initialize the Controller."""
        super().__init__()
        self.signals = signals

        self.worker: Optional[Backup.Worker] = None
        self._worker_thread: Optional[QThread] = None

        self.elapsed_timer = QTimer(self)
        self.elapsed_timer.timeout.connect(self._tick)
        self.elapsed_start_time: float = 0.0

        self.state: ControllerState = ControllerState.IDLE

    # =========================================================================
    # PRIVATE
    # =========================================================================

    def _set_state(self, new_state: ControllerState) -> bool:
        """Centralized FSM validation and state mutation."""
        if self.state == new_state:
            return True

        if new_state not in VALID_TRANSITIONS.get(self.state, set()):
            LOGGER.error(
                "Invalid FSM transition rejected: %s -> %s",
                self.state.name,
                new_state.name,
            )
            return False

        LOGGER.debug(
            "State transition: %s -> %s", 
            self.state.name,
            new_state.name
        )
        self.state = new_state
        return True

    def _force_state(self, new_state: ControllerState, reason: str = "") -> None:
        """Bypass FSM for shutdown/recovery paths where safety > correctness."""
        LOGGER.warning(
            "FORCED state transition: %s -> %s (%s)",
            self.state.name,
            new_state.name,
            reason,
        )
        self.state = new_state

    def _force_idle(self, reason: str = "") -> None:
        """Force transition to IDLE state."""
        self._force_state(ControllerState.IDLE, reason)

    def start_backup(self) -> None:
        """Start the backup process if not already running."""
        if self.state != ControllerState.IDLE:
            LOGGER.warning("Backup already in progress, ignoring request")
            return

        if not self._set_state(ControllerState.RUNNING):
            return

        LOGGER.info("Starting backup process")
        self.signals.backup_started.emit()

        try:
            self._start_elapsed_timer()
            self._deploy_worker()
        except Exception as error:
            LOGGER.error("Failed to start backup: %s", error)
            self._set_state(ControllerState.FAILED)
            self._request_worker_shutdown()
            self.signals.worker_error.emit(
                "Failed to initialize the backup process."
            )

    def cancel_backup(self) -> None:
        """Cancel the current backup operation."""
        if not self._set_state(ControllerState.CANCELLING):
            return

        LOGGER.info("Cancelling backup")
        self._stop_elapsed_timer()
        self._request_worker_shutdown(wait=True)

    def reset(self) -> None:
        """Explicitly recover from a FAILED state back to idle."""
        if self.state == ControllerState.FAILED:
            self._set_state(ControllerState.IDLE)

    def cleanup(self) -> None:
        """Perform full synchronous cleanup for application exit."""
        self._stop_elapsed_timer()
        if self.state != ControllerState.IDLE:
            self._force_idle("application shutdown")
            self._request_worker_shutdown(wait=True)

    # =========================================================================
    # WORKER MANAGEMENT
    # =========================================================================

    def _deploy_worker(self) -> None:
        """Create and start the worker thread."""
        if self.worker or self._worker_thread:
            self._request_worker_shutdown(wait=True)

        self.worker = Backup.Worker()
        self._worker_thread = QThread()
        self.worker.moveToThread(self._worker_thread)

        # Let QObject parent/child system handle signal disconnection natively
        self.worker.scanned_entries.connect(self.signals.scanned_entries)
        self.worker.estimated_size.connect(self.signals.estimated_size)
        self.worker.progress.connect(self.signals.progress)
        self.worker.disk_space_error.connect(self._handle_disk_space_error)
        self.worker.no_browsers_found.connect(self._handle_no_browsers)
        self.worker.failed.connect(self._handle_worker_failure)
        self.worker.done.connect(self._handle_worker_completion)

        self._worker_thread.started.connect(self.worker.run)

        # Native Qt thread-safe cleanup routing
        self._worker_thread.finished.connect(self.worker.deleteLater)
        self._worker_thread.finished.connect(self._worker_thread.deleteLater)
        self._worker_thread.finished.connect(self._handle_thread_finished)

        self._worker_thread.start()
        LOGGER.info("Worker thread deployed")

    def _request_worker_shutdown(self, wait: bool = False) -> bool:
        """Issue termination commands to active worker context safely."""
        if not self.worker and not self._worker_thread:
            return True

        if self.worker:
            try:
                self.worker.cancel()
            except Exception as e:
                LOGGER.warning("Worker cancel failed: %s", e)

        if self._worker_thread and self._worker_thread.isRunning():
            self._worker_thread.quit()
            if wait:
                if not self._worker_thread.wait(THREAD_WAIT_TIMEOUT_MS):
                    LOGGER.error("Worker thread hung! Forcing termination.")
                    self._worker_thread.terminate()
                    self._worker_thread.wait(500)
                    self._set_state(ControllerState.FAILED)
                    self.signals.worker_error.emit(
                        "The backup process timed out."
                    )
                    return False
        return True

    def _quit_worker_thread(self) -> None:
        """Request a clean worker-thread exit without re-cancelling work."""
        if self._worker_thread and self._worker_thread.isRunning():
            self._worker_thread.quit()

    def _handle_worker_completion(self) -> None:
        """Acknowledge normal completion of the worker.

        This is connected to ``worker.done`` and only fires for a
        successful pipeline completion.
        """
        if self.state != ControllerState.RUNNING:
            return

        if not self._set_state(ControllerState.SUCCESS):
            return

        LOGGER.info("Worker finished task")
        self._stop_elapsed_timer()
        self._quit_worker_thread()

    def _handle_worker_failure(self, message: str) -> None:
        """Handle worker-level failures that should fail the run."""
        if self.state == ControllerState.CANCELLING:
            return

        if self.state != ControllerState.RUNNING:
            LOGGER.warning(
                "Ignoring worker failure outside RUNNING state: %s",
                self.state.name,
            )
            return

        if not self._set_state(ControllerState.FAILED):
            return

        LOGGER.error("Worker reported failure: %s", message)
        self._stop_elapsed_timer()
        self.signals.worker_error.emit(message)
        self._quit_worker_thread()

    def _handle_thread_finished(self) -> None:
        """Evaluate final thread lifetime and fire bound states to the FSM."""
        self.worker = None
        self._worker_thread = None

        last_state = self.state

        if last_state == ControllerState.SUCCESS:
            self._set_state(ControllerState.IDLE)
            self.signals.backup_finished.emit()

        elif last_state == ControllerState.EMPTY:
            self._set_state(ControllerState.IDLE)

        elif last_state == ControllerState.BLOCKED:
            self._set_state(ControllerState.IDLE)

        elif last_state == ControllerState.CANCELLING:
            self._set_state(ControllerState.IDLE)
            self.signals.backup_cancelled.emit()

        elif last_state == ControllerState.FAILED:
            # Sticky — stays FAILED until reset() is called explicitly.
            LOGGER.error(
                "Pipeline ended in FAILED state. Call reset() to recover."
            )

        elif last_state == ControllerState.RUNNING:
            # Thread exited without a completion marker — unexpected crash.
            self._set_state(ControllerState.FAILED)
            LOGGER.error("Worker thread terminated unexpectedly")
            self._stop_elapsed_timer()
            self.signals.worker_error.emit(
                "The backup process experienced an unexpected error."
            )

    def _handle_disk_space_error(self, required: str, available: str) -> None:
        """Handle insufficient disk space — valid constraint, not a crash."""
        if not self._set_state(ControllerState.BLOCKED):
            return

        self._stop_elapsed_timer()
        self.signals.disk_space_error.emit(required, available)
        self._quit_worker_thread()

    def _handle_no_browsers(self) -> None:
        """Handle no browsers found — valid no-op, not a crash."""
        if not self._set_state(ControllerState.EMPTY):
            return

        self._stop_elapsed_timer()
        self.signals.no_browsers_found.emit()
        self._quit_worker_thread()

    # =========================================================================
    # ELAPSED TIMER
    # =========================================================================

    def _start_elapsed_timer(self) -> None:
        """Start the timer for elapsed time tracking safely."""
        self.elapsed_start_time = time.monotonic()
        try:
            if self.elapsed_timer and not self.elapsed_timer.isActive():
                self.elapsed_timer.start(UPDATE_INTERVAL_MS)
        except RuntimeError:
            pass

    def _stop_elapsed_timer(self) -> None:
        """Stop the elapsed timer safely."""
        try:
            if self.elapsed_timer and self.elapsed_timer.isActive():
                self.elapsed_timer.stop()
        except RuntimeError:
            pass

    def _tick(self) -> None:
        """Calculate elapsed time and emit."""
        if self.state != ControllerState.RUNNING:
            return

        elapsed = int(time.monotonic() - self.elapsed_start_time)
        if elapsed < 0:
            self.elapsed_start_time = time.monotonic()
            elapsed = 0
        self.signals.elapsed_time.emit(elapsed)
