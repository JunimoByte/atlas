"""Atlas | Tests | CLI.

Unit tests for cli.py covering execution flow, callbacks,
milestone tracking, TTY handling, and exit codes.
"""

# =============================================================================
# IMPORTS
# =============================================================================

import sys
from unittest.mock import MagicMock, patch

import pytest

from atlas import cli
from atlas.backup.pipeline import PipelineResult

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture(autouse=True)
def _reset_milestones() -> None:
    """Ensure milestone set is fresh before each test."""
    cli._LOGGED_MILESTONES.clear()


# =============================================================================
# TESTS — Clear Line & Callbacks
# =============================================================================


def test_clear_line_when_atty(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify clear_line writes spaces and flushes when on a TTY."""
    mock_stdout = MagicMock()
    mock_stdout.isatty.return_value = True
    monkeypatch.setattr(sys, "stdout", mock_stdout)

    cli.clear_line()

    mock_stdout.write.assert_called_once_with("\r" + " " * 79 + "\r")
    mock_stdout.flush.assert_called_once()


def test_clear_line_when_not_atty(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify clear_line does nothing when not on a TTY."""
    mock_stdout = MagicMock()
    mock_stdout.isatty.return_value = False
    monkeypatch.setattr(sys, "stdout", mock_stdout)

    cli.clear_line()

    mock_stdout.write.assert_not_called()
    mock_stdout.flush.assert_not_called()


def test_on_progress_atty(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify progress bar updates in-place when on a TTY."""
    mock_stdout = MagicMock()
    mock_stdout.isatty.return_value = True
    monkeypatch.setattr(sys, "stdout", mock_stdout)

    cli._on_progress(50, 100)

    mock_stdout.write.assert_called_once()
    assert "50%" in mock_stdout.write.call_args[0][0]
    mock_stdout.flush.assert_called_once()


def test_on_progress_non_atty_deduplicates(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
) -> None:
    """Verify milestones are printed only once per 10% step in non-TTY mode."""
    monkeypatch.setattr(sys.stdout, "isatty", lambda: False)

    # 10% milestone hit multiple times
    cli._on_progress(10, 100)
    cli._on_progress(10, 100)
    cli._on_progress(11, 100)  # 11% should not log
    cli._on_progress(20, 100)  # 20% should log

    captured = capsys.readouterr()
    lines = [line for line in captured.out.splitlines() if line.strip()]
    assert len(lines) == 2
    assert "10%" in lines[0]
    assert "20%" in lines[1]


def test_on_scanned_atty(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify scanning text writes and truncates when on a TTY."""
    mock_stdout = MagicMock()
    mock_stdout.isatty.return_value = True
    monkeypatch.setattr(sys, "stdout", mock_stdout)

    long_msg = "A" * 100
    cli._on_scanned(long_msg)

    mock_stdout.write.assert_called_once()
    written = mock_stdout.write.call_args[0][0]
    # '\r' + 78 padded characters = 79 characters total
    assert len(written) == 79
    assert "[Scanning]" in written


def test_on_scanned_non_atty(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify scanning output is suppressed in non-TTY mode."""
    mock_stdout = MagicMock()
    mock_stdout.isatty.return_value = False
    monkeypatch.setattr(sys, "stdout", mock_stdout)

    cli._on_scanned("some/path")
    mock_stdout.write.assert_not_called()


# =============================================================================
# TESTS — run_cli Execution Flow
# =============================================================================


def test_run_cli_fails_on_invalid_browsers() -> None:
    """Verify exit code 1 when browser configuration fails validation."""
    with patch("atlas.lib.browsers.verify_entries", return_value=False):
        assert cli.run_cli() == 1


def test_run_cli_success() -> None:
    """Verify exit code 0 when pipeline run succeeds."""
    with patch("atlas.lib.browsers.verify_entries", return_value=True):
        with patch("atlas.lib.permissions.is_elevated", return_value=False):
            with patch("atlas.cli.Pipeline") as mock_pipeline_cls:
                mock_inst = MagicMock()
                mock_inst.run.return_value = PipelineResult.SUCCESS
                mock_pipeline_cls.return_value = mock_inst

                assert cli.run_cli() == 0


def test_run_cli_cancelled() -> None:
    """Verify exit code 1 when pipeline reports CANCELLED."""
    with patch("atlas.lib.browsers.verify_entries", return_value=True):
        with patch("atlas.lib.permissions.is_elevated", return_value=False):
            with patch("atlas.cli.Pipeline") as mock_pipeline_cls:
                mock_inst = MagicMock()
                mock_inst.run.return_value = PipelineResult.CANCELLED
                mock_pipeline_cls.return_value = mock_inst

                assert cli.run_cli() == 1


def test_run_cli_keyboard_interrupt() -> None:
    """Verify graceful handling and exit code 1 on KeyboardInterrupt."""
    with patch("atlas.lib.browsers.verify_entries", return_value=True):
        with patch("atlas.lib.permissions.is_elevated", return_value=False):
            with patch("atlas.cli.Pipeline") as mock_pipeline_cls:
                mock_inst = MagicMock()
                mock_inst.run.side_effect = KeyboardInterrupt
                mock_pipeline_cls.return_value = mock_inst

                assert cli.run_cli() == 1
                mock_inst.cancel.assert_called_once()
