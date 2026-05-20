"""Unit tests for the Worker backup thread in atlas.backup.worker.

Covers signal emissions, cancellation, and the run() workflow.
"""

# =============================================================================
# IMPORTS
# =============================================================================

import sys
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest
from PyQt6.QtWidgets import QApplication

from atlas.backup.pipeline import PipelineResult
from atlas.backup.worker import Worker

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture(scope="session")
def qapp() -> Generator[QApplication, None, None]:
    """Provide a session-scoped QApplication instance for Qt signal tests."""
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def mock_pipeline_cls() -> Generator[MagicMock, None, None]:
    """Mock the Pipeline class used by Worker."""
    with patch("atlas.backup.worker.Pipeline") as mock:
        yield mock


@pytest.fixture
def worker(qapp: QApplication) -> Worker:
    """Return a default Worker."""
    return Worker()


# =============================================================================
# TESTS — Cancel
# =============================================================================


def test_cancel_calls_pipeline_cancel(worker: Worker) -> None:
    """Verify that worker cancellation propagates to the pipeline."""
    mock_pipeline = MagicMock()
    worker._pipeline = mock_pipeline
    worker.cancel()
    mock_pipeline.cancel.assert_called_once()


def test_cancel_emits_cancelled_signal(worker: Worker) -> None:
    """Verify that a signal is emitted upon cancellation."""
    received = []
    worker.cancelled.connect(lambda: received.append(True))
    worker.cancel()
    assert received == [True]


# =============================================================================
# TESTS — No browsers found
# =============================================================================


def test_run_emits_no_browsers_found_when_empty(
    worker: Worker, mock_pipeline_cls: MagicMock
) -> None:
    """Verify that no_browsers_found is emitted when no profiles exist."""
    def trigger_no_browsers(*args, **kwargs):
        worker.no_browsers_found.emit()
        return PipelineResult.NO_BROWSERS_FOUND

    mock_instance = mock_pipeline_cls.return_value
    mock_instance.run.side_effect = trigger_no_browsers

    done_calls = []
    received = []
    worker.done.connect(lambda: done_calls.append(True))
    worker.no_browsers_found.connect(lambda: received.append(True))
    worker.run()

    assert done_calls == []
    assert received == [True]


# =============================================================================
# TESTS — Disk space error
# =============================================================================


def test_run_emits_disk_space_error_when_insufficient(
    worker: Worker, mock_pipeline_cls: MagicMock
) -> None:
    """Verify that disk_space_error is emitted on failure."""
    def trigger_disk_error(*args, **kwargs):
        worker.disk_space_error.emit("15 GB", "1 MB")
        return PipelineResult.INSUFFICIENT_DISK_SPACE

    mock_instance = mock_pipeline_cls.return_value
    mock_instance.run.side_effect = trigger_disk_error

    done_calls = []
    received = []
    worker.done.connect(lambda: done_calls.append(True))
    worker.disk_space_error.connect(lambda r, a: received.append((r, a)))
    worker.run()

    assert done_calls == []
    assert len(received) == 1
    assert received[0] == ("15 GB", "1 MB")


# =============================================================================
# TESTS — Run success
# =============================================================================


def test_run_emits_done_on_success(
    worker: Worker, mock_pipeline_cls: MagicMock
) -> None:
    """Verify that done is emitted upon success."""
    mock_instance = mock_pipeline_cls.return_value
    mock_instance.run.return_value = PipelineResult.SUCCESS

    done_calls = []
    worker.done.connect(lambda: done_calls.append(True))
    worker.run()

    assert done_calls == [True]
    mock_instance.run.assert_called_once()


# =============================================================================
# TESTS — Cancelled
# =============================================================================


def test_run_does_not_emit_done_when_cancelled(
    worker: Worker, mock_pipeline_cls: MagicMock
) -> None:
    """Verify that cancellation does not emit a success signal."""
    mock_instance = mock_pipeline_cls.return_value
    mock_instance.run.return_value = PipelineResult.CANCELLED

    done_calls = []
    no_browsers = []
    worker.done.connect(lambda: done_calls.append(True))
    worker.no_browsers_found.connect(lambda: no_browsers.append(True))

    worker.run()

    assert done_calls == []
    assert no_browsers == []


# =============================================================================
# TESTS — Exception handling
# =============================================================================


def test_run_emits_failed_on_unexpected_exception(
    worker: Worker, mock_pipeline_cls: MagicMock
) -> None:
    """Verify that unexpected errors emit a failure signal."""
    mock_instance = mock_pipeline_cls.return_value
    mock_instance.run.side_effect = RuntimeError("boom")

    failures = []
    worker.failed.connect(lambda message: failures.append(message))
    worker.run()

    assert failures == ["The backup process experienced an unexpected error."]


def test_run_emits_failed_when_pipeline_reports_failure(
    worker: Worker, mock_pipeline_cls: MagicMock
) -> None:
    """Verify that pipeline failures do not emit done."""
    mock_instance = mock_pipeline_cls.return_value
    mock_instance.run.return_value = PipelineResult.FAILED

    done_calls = []
    failures = []
    worker.done.connect(lambda: done_calls.append(True))
    worker.failed.connect(lambda message: failures.append(message))
    worker.run()

    assert done_calls == []
    assert failures == [
        "The backup process could not complete successfully."
    ]


# =============================================================================
# TEST EXECUTION
# =============================================================================

if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
