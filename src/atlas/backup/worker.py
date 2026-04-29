"""Atlas | Backup | Worker.

Background worker layer for the backup process.
Wraps the logical Pipeline with PyQt signals for UI integration.
"""

# =============================================================================
# IMPORTS
# =============================================================================

import logging

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
    """Worker thread for running the backup pipeline.

    Connect pipeline callbacks to PyQt signals to update the UI
    without freezing the main thread.
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
        """Initialize the Worker and the underlying Pipeline."""
        super().__init__()
        self.pipeline = Pipeline(
            progress_callback=self.progress.emit,
            scanned_callback=self.scanned_entries.emit,
            estimated_callback=self.estimated_size.emit,
            no_browsers_found_callback=self.no_browsers_found.emit,
            disk_space_error_callback=self.disk_space_error.emit
        )

    # =========================================================================
    # PUBLIC METHODS
    # =========================================================================

    def cancel(self) -> None:
        """Cancel the running worker.

        Propagate the cancellation request to the pipeline and
        emit the cancelled signal.
        """
        self.pipeline.cancel()
        self.cancelled.emit()

    def run(self) -> None:
        """Run the backup process.

        Execute the pipeline and handle final signal emission.
        """
        try:
            LOGGER.info("Worker started")
            result = self.pipeline.run()
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

        LOGGER.info("Worker finished.")
