"""Atlas | Backup | Worker.

Background worker layer for the backup process.
Wraps the Qt-free Pipeline with PyQt signals for UI integration.
"""

# =============================================================================
# IMPORTS
# =============================================================================

import logging
from typing import Optional

from PyQt6.QtCore import QObject, pyqtSignal

from atlas.backup.pipeline import Pipeline, PipelineResult

# =============================================================================
# LOGGING
# =============================================================================

LOGGER = logging.getLogger(__name__)

# =============================================================================
# CLASSES
# =============================================================================


class Worker(QObject):
    """Qt adapter that runs the backup pipeline on a background thread.

    Wires pyqtSignals as plain-Python callbacks into the Qt-free
    Pipeline.  The GUI path uses this class via QThread.  CI and
    headless callers use atlas.backup.runner directly.
    """

    progress = pyqtSignal(int, int)
    done = pyqtSignal()
    estimated_size = pyqtSignal(str)
    scanned_entries = pyqtSignal(str)
    disk_space_error = pyqtSignal(str, str)
    no_browsers_found = pyqtSignal()
    cancelled = pyqtSignal()
    failed = pyqtSignal(str)

    def __init__(self) -> None:
        """Initialize the Worker."""
        super().__init__()
        self._pipeline: Optional[Pipeline] = None

    # =========================================================================
    # PUBLIC METHODS
    # =========================================================================

    def cancel(self) -> None:
        """Cancel the running pipeline and emit the cancelled signal.

        Thread-safe: ``_pipeline`` is stored before ``pipeline.run()``
        starts and cleared in a ``finally`` block, so this will always
        reach a live instance while the pipeline is executing.
        """
        if self._pipeline is not None:
            self._pipeline.cancel()
        self.cancelled.emit()

    def run(self) -> None:
        """Run the backup pipeline on the current thread.

        Constructs a Pipeline with signal-driven callbacks, stores it
        for cancellation access, and translates the final result into
        the appropriate pyqtSignal emission.
        """
        LOGGER.info("Worker started")
        try:
            self._pipeline = Pipeline(
                progress_callback=self.progress.emit,
                scanned_callback=self.scanned_entries.emit,
                estimated_callback=self.estimated_size.emit,
                no_browsers_found_callback=self.no_browsers_found.emit,
                disk_space_error_callback=self.disk_space_error.emit,
            )
            result = self._pipeline.run()

            if result == PipelineResult.SUCCESS:
                self.done.emit()
            elif result == PipelineResult.FAILED:
                self.failed.emit(
                    "The backup process could not complete successfully."
                )
            elif result not in (
                PipelineResult.CANCELLED,
                PipelineResult.NO_BROWSERS_FOUND,
                PipelineResult.INSUFFICIENT_DISK_SPACE,
            ):
                self.failed.emit(
                    "The backup process ended in an invalid state."
                )
        except Exception as error:
            LOGGER.error("Worker.run crashed: %s", error, exc_info=True)
            self.failed.emit(
                "The backup process experienced an unexpected error."
            )
        finally:
            self._pipeline = None

        LOGGER.info("Worker finished.")
