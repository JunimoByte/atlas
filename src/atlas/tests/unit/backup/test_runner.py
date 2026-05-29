"""Unit tests for the runner in atlas.backup.runner."""

import sys
from unittest.mock import MagicMock, patch

import pytest

from atlas.backup.pipeline import PipelineResult
from atlas.backup.runner import run_pipeline


@patch("atlas.backup.runner.Pipeline")
def test_run_pipeline_success(mock_pipeline_cls: MagicMock) -> None:
    """Verify that run_pipeline initializes Pipeline and returns a success result."""
    mock_pipeline = mock_pipeline_cls.return_value
    mock_pipeline.run.return_value = PipelineResult.SUCCESS

    result, pipeline = run_pipeline()

    assert result == PipelineResult.SUCCESS
    assert pipeline is mock_pipeline
    mock_pipeline.run.assert_called_once()


@patch("atlas.backup.runner.Pipeline")
def test_run_pipeline_failure(mock_pipeline_cls: MagicMock) -> None:
    """Verify that an exception raised by pipeline run returns FAILED."""
    mock_pipeline = mock_pipeline_cls.return_value
    mock_pipeline.run.side_effect = RuntimeError("boom")

    result, pipeline = run_pipeline()

    assert result == PipelineResult.FAILED
    assert pipeline is mock_pipeline


@patch("atlas.backup.runner.Pipeline")
def test_run_pipeline_initialization_failure(mock_pipeline_cls: MagicMock) -> None:
    """Verify that a Pipeline instantiation failure safely returns FAILED."""
    mock_pipeline_cls.side_effect = ValueError("bad args")

    result, pipeline = run_pipeline()

    assert result == PipelineResult.FAILED
    assert pipeline is None


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
