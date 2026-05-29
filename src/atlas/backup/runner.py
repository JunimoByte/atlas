"""Atlas | Backup | Runner.

Qt-free pipeline entry point for headless and CI execution.

This module owns the pipeline lifecycle without any dependency on PyQt.
The GUI path (Worker) delegates to this module. CI and tests can call
run_pipeline() directly without a QApplication.
"""

# =============================================================================
# IMPORTS
# =============================================================================

import logging
from typing import Callable, Optional, Tuple

from atlas.backup.pipeline import Pipeline, PipelineResult

# =============================================================================
# LOGGING
# =============================================================================

LOGGER = logging.getLogger(__name__)

# =============================================================================
# FUNCTIONS
# =============================================================================


def run_pipeline(
    progress_callback: Optional[Callable[[int, int], None]] = None,
    scanned_callback: Optional[Callable[[str], None]] = None,
    estimated_callback: Optional[Callable[[str], None]] = None,
    no_browsers_found_callback: Optional[Callable[[], None]] = None,
    disk_space_error_callback: Optional[
        Callable[[str, str], None]
    ] = None,
) -> Tuple[PipelineResult, Optional[Pipeline]]:
    """Execute the backup pipeline without any Qt dependency.

    Constructs and runs a :class:`Pipeline` with the supplied plain-Python
    callbacks.  The live ``Pipeline`` instance is returned alongside the
    result so that callers that need cooperative cancellation can call
    ``pipeline.cancel()`` from another thread.

    Args:
        progress_callback: Invoked with ``(current, total)`` as files
            are archived.
        scanned_callback: Invoked with a human-readable status string
            during the browser-profile scan phase.
        estimated_callback: Invoked with a formatted size string after
            the size estimate is complete.
        no_browsers_found_callback: Invoked when no valid browser
            profiles are detected.
        disk_space_error_callback: Invoked with ``(required, available)``
            formatted strings when free disk space is insufficient.

    Returns:
        A ``(PipelineResult, pipeline)`` tuple.  ``pipeline`` is ``None``
        if construction failed before the run started.

    """
    pipeline: Optional[Pipeline] = None
    try:
        pipeline = Pipeline(
            progress_callback=progress_callback,
            scanned_callback=scanned_callback,
            estimated_callback=estimated_callback,
            no_browsers_found_callback=no_browsers_found_callback,
            disk_space_error_callback=disk_space_error_callback,
        )
        result = pipeline.run()
        return result, pipeline
    except Exception as error:
        LOGGER.error(
            "run_pipeline failed unexpectedly: %s", error, exc_info=True
        )
        return PipelineResult.FAILED, pipeline
