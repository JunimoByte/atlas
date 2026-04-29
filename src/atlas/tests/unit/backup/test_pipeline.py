"""Atlas | Tests | Backup | Pipeline.

Unit tests for backup/pipeline.py.
Covers scan, estimate, backup phases, cancellation, and retry logic.
"""

# =============================================================================
# IMPORTS
# =============================================================================

import sys
from unittest.mock import MagicMock, patch

import pytest

from atlas.backup.pipeline import Pipeline, PipelineResult

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def pipeline() -> Pipeline:
    """Return a Pipeline with no callbacks and a mocked browser list."""
    with patch(
        "atlas.backup.pipeline.browsers.grab",
        return_value={"Chrome": {}, "Firefox": {}}
    ):
        p = Pipeline()
    return p


@pytest.fixture
def empty_pipeline() -> Pipeline:
    """Return a Pipeline with no browsers."""
    with patch("atlas.backup.pipeline.browsers.grab", return_value={}):
        p = Pipeline()
    return p


# =============================================================================
# TESTS — Cancellation
# =============================================================================


def test_cancel_sets_flag(pipeline: Pipeline) -> None:
    """Verify that cancel() sets the internal flag."""
    assert pipeline._cancelled is False
    pipeline.cancel()
    assert pipeline._cancelled is True


@pytest.mark.parametrize(
    "pre_cancel, expected",
    [
        (True, True),
        (False, False),
    ]
)
def test_check_cancelled_state(
    pipeline: Pipeline, pre_cancel: bool, expected: bool
) -> None:
    """Verify the cancellation state check."""
    if pre_cancel:
        pipeline.cancel()
    assert pipeline.is_cancelled() is expected


@pytest.mark.parametrize(
    "method_name, call_args",
    [
        ("scan_profiles", []),
        ("estimate_size", [{"Chrome": ["/some/path"]}]),
    ]
)
def test_cancelled_pipeline_returns_early(
    pipeline: Pipeline, method_name: str, call_args: list
) -> None:
    """Verify that methods return early when cancelled."""
    pipeline.cancel()
    result = getattr(pipeline, method_name)(*call_args)
    assert result in ({}, 0)


# =============================================================================
# TESTS — Emit
# =============================================================================


def test_emit_calls_callback(pipeline: Pipeline) -> None:
    """Verify that the callback is invoked with arguments."""
    mock = MagicMock()
    pipeline._emit(mock, "hello", 42)
    mock.assert_called_once_with("hello", 42)


def test_emit_does_nothing_when_callback_is_none(pipeline: Pipeline) -> None:
    """Ensure that no error occurs when the callback is None."""
    pipeline._emit(None, "arg")  # Should not raise


# =============================================================================
# TESTS — Retry operation
# =============================================================================


def test_retry_operation_succeeds_on_first_try(pipeline: Pipeline) -> None:
    """Verify that success returns immediately."""
    assert pipeline._retry_operation(lambda: 42) == 42


def test_retry_operation_retries_on_generic_error(pipeline: Pipeline) -> None:
    """Verify retry logic on generic errors."""
    call_count = {"n": 0}

    def flaky():
        """Fail twice before succeeding."""
        call_count["n"] += 1
        if call_count["n"] < 3:
            raise RuntimeError("transient error")
        return "ok"

    with patch("atlas.backup.pipeline.time.sleep"):
        result = pipeline._retry_operation(flaky)

    assert result == "ok"
    assert call_count["n"] == 3


def test_retry_operation_does_not_retry_permission_error(
    pipeline: Pipeline
) -> None:
    """Verify that PermissionError is raised without retries."""
    call_count = {"n": 0}

    def raises():
        """Raise PermissionError always."""
        call_count["n"] += 1
        raise PermissionError("denied")

    with pytest.raises(PermissionError):
        pipeline._retry_operation(raises)

    assert call_count["n"] == 1


def test_retry_operation_raises_after_all_retries_fail(
    pipeline: Pipeline
) -> None:
    """Verify that exhaustively failed retries raise an error."""
    with patch("atlas.backup.pipeline.time.sleep"):
        with pytest.raises(RuntimeError):
            pipeline._retry_operation(
                lambda: (_ for _ in ()).throw(RuntimeError("always fails"))
            )


# =============================================================================
# TESTS — Scan profiles
# =============================================================================


def test_scan_profiles_returns_dict(pipeline: Pipeline) -> None:
    """Verify that scan_profiles returns a dictionary."""
    with patch("atlas.backup.pipeline.Profile.find_profile", return_value=[]):
        result = pipeline.scan_profiles()
    assert isinstance(result, dict)


def test_scan_profiles_populates_matches(pipeline: Pipeline) -> None:
    """Verify that profile matches are populated."""
    with patch(
        "atlas.backup.pipeline.Profile.find_profile",
        return_value=["/fake/profile/path"]
    ):
        result = pipeline.scan_profiles()

    assert len(result) > 0
    for paths in result.values():
        assert "/fake/profile/path" in paths


# =============================================================================
# TESTS — Estimate size
# =============================================================================


def test_estimate_size_sums_sizes(pipeline: Pipeline) -> None:
    """Verify size estimation and callback emission."""
    emitted = []
    pipeline.estimated_callback = emitted.append

    with patch(
        "atlas.backup.pipeline.Size.get_directory_size",
        return_value=1024
    ):
        with patch(
            "atlas.backup.pipeline.Size.format_size",
            return_value="1 KB"
        ):
            result = pipeline.estimate_size({"Chrome": ["/path/a"]})

    assert result == 1024
    assert "1 KB" in emitted


def test_estimate_size_returns_zero_for_empty_matches(
    pipeline: Pipeline
) -> None:
    """Verify that empty matches result in zero size."""
    result = pipeline.estimate_size({})
    assert result == 0


# =============================================================================
# TESTS — Perform backup
# =============================================================================


def test_perform_backup_calls_compress_per_browser(pipeline: Pipeline) -> None:
    """Verify that compression is called per browser."""
    matches = {"Chrome": ["/path/a"], "Firefox": ["/path/b"]}
    with patch(
        "atlas.backup.pipeline.archive.compress",
        return_value="/output/Chrome.zip"
    ) as mock_c:
        pipeline.perform_backup(matches)

    assert mock_c.call_count == 2


def test_perform_backup_emits_progress(pipeline: Pipeline) -> None:
    """Verify progress callback reporting."""
    calls = []
    pipeline.progress_callback = lambda cur, tot: calls.append((cur, tot))

    with patch(
        "atlas.backup.pipeline.archive.compress",
        return_value="/out/x.zip"
    ):
        pipeline.perform_backup({"Chrome": ["/p"]})

    assert calls == [(1, 1)]


def test_perform_backup_stops_on_cancel(pipeline: Pipeline) -> None:
    """Verify that backup stops when cancelled."""
    pipeline.cancel()
    with patch("atlas.backup.pipeline.archive.compress") as mock_c:
        result = pipeline.perform_backup({"Chrome": ["/p"]})
    mock_c.assert_not_called()
    assert result is False


def test_perform_backup_returns_false_on_archive_failure(
    pipeline: Pipeline
) -> None:
    """Return False when a browser archive could not be created."""
    with patch(
        "atlas.backup.pipeline.archive.compress",
        return_value=None,
    ):
        result = pipeline.perform_backup({"Chrome": ["/p"]})

    assert result is False


# =============================================================================
# TESTS — Repr
# =============================================================================


def test_pipeline_repr(pipeline: Pipeline) -> None:
    """Verify the string representation of the pipeline."""
    r = repr(pipeline)
    assert "Pipeline" in r
    assert "cancelled" in r


# =============================================================================
# TESTS - Run outcome
# =============================================================================


def test_run_returns_success_when_backup_completes(
    pipeline: Pipeline
) -> None:
    """Return SUCCESS when every pipeline stage completes."""
    with patch.object(
        pipeline, "scan_profiles", return_value={"Chrome": ["/p"]}
    ):
        with patch.object(pipeline, "estimate_size", return_value=1024):
            with patch.object(
                pipeline, "_verify_disk_space", return_value=True
            ):
                with patch.object(
                    pipeline, "perform_backup", return_value=True
                ):
                    result = pipeline.run()

    assert result == PipelineResult.SUCCESS


def test_run_returns_failed_when_backup_phase_fails(
    pipeline: Pipeline
) -> None:
    """Return FAILED when the backup phase does not complete."""
    with patch.object(
        pipeline, "scan_profiles", return_value={"Chrome": ["/p"]}
    ):
        with patch.object(pipeline, "estimate_size", return_value=1024):
            with patch.object(
                pipeline, "_verify_disk_space", return_value=True
            ):
                with patch.object(
                    pipeline, "perform_backup", return_value=False
                ):
                    result = pipeline.run()

    assert result == PipelineResult.FAILED


def test_run_returns_no_browsers_found_when_scan_is_empty(
    pipeline: Pipeline
) -> None:
    """Return NO_BROWSERS_FOUND when scanning finds no profiles."""
    with patch.object(pipeline, "scan_profiles", return_value={}):
        result = pipeline.run()

    assert result == PipelineResult.NO_BROWSERS_FOUND


def test_run_returns_insufficient_disk_space_when_check_fails(
    pipeline: Pipeline
) -> None:
    """Return INSUFFICIENT_DISK_SPACE when free space is too low."""
    with patch.object(
        pipeline, "scan_profiles", return_value={"Chrome": ["/p"]}
    ):
        with patch.object(pipeline, "estimate_size", return_value=1024):
            with patch.object(
                pipeline, "_verify_disk_space", return_value=False
            ):
                result = pipeline.run()

    assert result == PipelineResult.INSUFFICIENT_DISK_SPACE


# =============================================================================
# TEST EXECUTION
# =============================================================================

if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
