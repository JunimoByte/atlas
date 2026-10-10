"""Atlas | Tests | CLI.

Unit tests for cli.py covering execution flow, callbacks,
milestone tracking, TTY handling, and exit codes.
"""

# =============================================================================
# IMPORTS
# =============================================================================

import argparse
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from atlas import cli
from atlas.backup import archive
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


def test_run_cli_custom_output_success(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    """Verify run_cli configures custom output directory when requested."""
    target_dir = tmp_path / "custom_cli_out"
    args = argparse.Namespace(output=str(target_dir))

    with patch("atlas.lib.browsers.verify_entries", return_value=True):
        with patch("atlas.lib.permissions.is_elevated", return_value=False):
            with patch("atlas.cli.Pipeline") as mock_pipeline_cls:
                mock_inst = MagicMock()
                mock_inst.run.return_value = PipelineResult.SUCCESS
                mock_pipeline_cls.return_value = mock_inst

                try:
                    code = cli.run_cli(args)
                    assert code == 0
                    assert (
                        archive.get_zip_output_dir()
                        == target_dir.resolve()
                    )
                    captured = capsys.readouterr()
                    assert "Output Directory:" in captured.out
                finally:
                    archive.set_zip_output_dir(None)


def test_run_cli_invalid_output_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    """Verify run_cli fails fast when output directory is invalid."""
    existing_file = tmp_path / "blocked.txt"
    existing_file.write_text("not a dir")
    args = argparse.Namespace(output=str(existing_file))

    with patch("atlas.lib.browsers.verify_entries", return_value=True):
        with patch("atlas.lib.permissions.is_elevated", return_value=False):
            code = cli.run_cli(args)
            assert code == 1
            captured = capsys.readouterr()
            assert "Error: Invalid output directory" in captured.out


def test_run_list_with_matches(capsys: pytest.CaptureFixture) -> None:
    """Verify run_list prints detected profiles and total size."""
    args = argparse.Namespace(list=True)
    matches = {
        "Brave": ["/home/user/.config/BraveSoftware"],
        "Chrome": ["/home/user/.config/google-chrome"],
    }
    with patch("atlas.lib.browsers.verify_entries", return_value=True):
        with patch("atlas.lib.permissions.is_elevated", return_value=False):
            with patch("atlas.cli.Pipeline") as mock_pipeline_cls:
                mock_inst = MagicMock()
                mock_inst.scan_profiles.return_value = matches
                mock_inst.estimate_size.return_value = 1048576
                mock_pipeline_cls.return_value = mock_inst

                assert cli.run_list(args) == 0
                captured = capsys.readouterr()
                assert "[Brave]" in captured.out
                assert "[Chrome]" in captured.out
                assert "Total Profiles: 2" in captured.out
                assert "Estimated Size: 1 MB" in captured.out


def test_run_list_no_matches(capsys: pytest.CaptureFixture) -> None:
    """Verify run_list prints message when no profiles are found."""
    args = argparse.Namespace(list=True)
    with patch("atlas.lib.browsers.verify_entries", return_value=True):
        with patch("atlas.lib.permissions.is_elevated", return_value=False):
            with patch("atlas.cli.Pipeline") as mock_pipeline_cls:
                mock_inst = MagicMock()
                mock_inst.scan_profiles.return_value = {}
                mock_pipeline_cls.return_value = mock_inst

                assert cli.run_list(args) == 0
                captured = capsys.readouterr()
                assert "No supported browser profiles found" in captured.out


def test_run_list_verify_fails(capsys: pytest.CaptureFixture) -> None:
    """Verify run_list returns 1 when browser verification fails."""
    args = argparse.Namespace(list=True)
    with patch("atlas.lib.browsers.verify_entries", return_value=False):
        assert cli.run_list(args) == 1
        captured = capsys.readouterr()
        assert "Error: Failed to load browser configuration." in captured.out


def test_run_list_keyboard_interrupt_scan(
    capsys: pytest.CaptureFixture,
) -> None:
    """Verify run_list handles KeyboardInterrupt during scanning cleanly."""
    args = argparse.Namespace(list=True)
    with patch("atlas.lib.browsers.verify_entries", return_value=True):
        with patch("atlas.lib.permissions.is_elevated", return_value=False):
            with patch("atlas.cli.Pipeline") as mock_pipeline_cls:
                mock_inst = MagicMock()
                mock_inst.scan_profiles.side_effect = KeyboardInterrupt
                mock_pipeline_cls.return_value = mock_inst

                assert cli.run_list(args) == 1
                captured = capsys.readouterr()
                assert "Scan cancelled by user." in captured.out


def test_run_list_keyboard_interrupt_size(
    capsys: pytest.CaptureFixture,
) -> None:
    """Verify run_list handles KeyboardInterrupt during size estimation."""
    args = argparse.Namespace(list=True)
    with patch("atlas.lib.browsers.verify_entries", return_value=True):
        with patch("atlas.lib.permissions.is_elevated", return_value=False):
            with patch("atlas.cli.Pipeline") as mock_pipeline_cls:
                mock_inst = MagicMock()
                mock_inst.scan_profiles.return_value = {"Brave": ["/path"]}
                mock_inst.estimate_size.side_effect = KeyboardInterrupt
                mock_pipeline_cls.return_value = mock_inst

                assert cli.run_list(args) == 1
                captured = capsys.readouterr()
                assert "Size estimation cancelled by user." in captured.out


def test_run_list_elevated_warning(capsys: pytest.CaptureFixture) -> None:
    """Verify run_list warns when executed with elevated privileges."""
    args = argparse.Namespace(list=True)
    with patch("atlas.lib.browsers.verify_entries", return_value=True):
        with patch("atlas.lib.permissions.is_elevated", return_value=True):
            with patch("atlas.cli.Pipeline") as mock_pipeline_cls:
                mock_inst = MagicMock()
                mock_inst.scan_profiles.return_value = {}
                mock_pipeline_cls.return_value = mock_inst

                cli.run_list(args)
                captured = capsys.readouterr()
                assert "WARNING: Running with elevated privileges" in (
                    captured.out
                )


def test_run_cli_dispatches_to_run_list() -> None:
    """Verify run_cli routes to run_list when args.list is True."""
    args = argparse.Namespace(list=True)
    with patch("atlas.cli.run_list", return_value=0) as mock_list:
        assert cli.run_cli(args) == 0
        mock_list.assert_called_once_with(args)


def test_run_cli_dispatches_to_run_backup() -> None:
    """Verify run_cli routes to run_backup by default."""
    args = argparse.Namespace(list=False)
    with patch("atlas.cli.run_backup", return_value=0) as mock_backup:
        assert cli.run_cli(args) == 0
        mock_backup.assert_called_once_with(args)


def test_print_banner(capsys: pytest.CaptureFixture) -> None:
    """Verify _print_banner renders centered title with ASCII borders."""
    cli._print_banner("TEST TITLE")
    captured = capsys.readouterr()
    lines = captured.out.strip().splitlines()
    assert len(lines) == 3
    assert lines[0] == "=" * 40
    assert "TEST TITLE" in lines[1]
    assert lines[2] == "=" * 40


def test_print_banner_quiet(capsys: pytest.CaptureFixture) -> None:
    """Verify _print_banner outputs nothing when quiet is True."""
    cli._print_banner("TEST TITLE", quiet=True)
    captured = capsys.readouterr()
    assert captured.out == ""


def test_is_quiet_helper() -> None:
    """Verify _is_quiet correctly evaluates Namespace quiet attribute."""
    assert cli._is_quiet(None) is False
    assert cli._is_quiet(argparse.Namespace()) is False
    assert cli._is_quiet(argparse.Namespace(quiet=False)) is False
    assert cli._is_quiet(argparse.Namespace(quiet=True)) is True


def test_run_backup_quiet_success(capsys: pytest.CaptureFixture) -> None:
    """Verify run_backup produces no stdout output in quiet mode."""
    args = argparse.Namespace(quiet=True, list=False)
    with patch("atlas.lib.browsers.verify_entries", return_value=True):
        with patch("atlas.lib.permissions.is_elevated", return_value=False):
            with patch("atlas.cli.Pipeline") as mock_pipeline_cls:
                mock_inst = MagicMock()
                mock_inst.browsers = {"Firefox": {}}
                mock_inst.run.return_value = PipelineResult.SUCCESS
                mock_pipeline_cls.return_value = mock_inst

                assert cli.run_backup(args) == 0
                captured = capsys.readouterr()
                assert captured.out == ""
                assert captured.err == ""


def test_run_backup_target_browser_not_found(
    capsys: pytest.CaptureFixture,
) -> None:
    """Verify run_backup fails fast when requested browser is unknown."""
    args = argparse.Namespace(browser="nonexistent", quiet=False, list=False)
    with patch("atlas.lib.browsers.verify_entries", return_value=True):
        with patch("atlas.lib.permissions.is_elevated", return_value=False):
            with patch("atlas.cli.Pipeline") as mock_pipeline_cls:
                mock_inst = MagicMock()
                mock_inst.browsers = {}
                mock_pipeline_cls.return_value = mock_inst

                assert cli.run_backup(args) == 1
                captured = capsys.readouterr()
                assert "Error: No browser found matching 'nonexistent'." in (
                    captured.out
                )


def test_run_list_target_browser_not_found(
    capsys: pytest.CaptureFixture,
) -> None:
    """Verify run_list fails fast when requested browser is unknown."""
    args = argparse.Namespace(browser="nonexistent", quiet=False, list=True)
    with patch("atlas.lib.browsers.verify_entries", return_value=True):
        with patch("atlas.lib.permissions.is_elevated", return_value=False):
            with patch("atlas.cli.Pipeline") as mock_pipeline_cls:
                mock_inst = MagicMock()
                mock_inst.browsers = {}
                mock_pipeline_cls.return_value = mock_inst

                assert cli.run_list(args) == 1
                captured = capsys.readouterr()
                assert "Error: No browser found matching 'nonexistent'." in (
                    captured.out
                )


def test_run_list_quiet(capsys: pytest.CaptureFixture) -> None:
    """Verify run_list suppresses ASCII banners when quiet is True."""
    args = argparse.Namespace(quiet=True, list=True, browser=None)
    matches = {"Firefox": ["/path/to/profile"]}
    with patch("atlas.lib.browsers.verify_entries", return_value=True):
        with patch("atlas.lib.permissions.is_elevated", return_value=False):
            with patch("atlas.cli.Pipeline") as mock_pipeline_cls:
                mock_inst = MagicMock()
                mock_inst.browsers = {"Firefox": {}}
                mock_inst.scan_profiles.return_value = matches
                mock_inst.estimate_size.return_value = 1048576
                mock_pipeline_cls.return_value = mock_inst

                assert cli.run_list(args) == 0
                captured = capsys.readouterr()
                assert "[Firefox]" in captured.out
                assert "=" * 40 not in captured.out


def test_run_list_json(capsys: pytest.CaptureFixture) -> None:
    """Verify run_list outputs structured JSON when requested."""
    args = argparse.Namespace(json=True, quiet=False, list=True, browser=None)
    matches = {"Firefox": ["/path/to/profile"]}
    with patch("atlas.lib.browsers.verify_entries", return_value=True):
        with patch("atlas.lib.permissions.is_elevated", return_value=False):
            with patch("atlas.cli.Pipeline") as mock_pipeline_cls:
                mock_inst = MagicMock()
                mock_inst.browsers = {"Firefox": {}}
                mock_inst.scan_profiles.return_value = matches
                mock_inst.estimate_size.return_value = 1048576
                mock_pipeline_cls.return_value = mock_inst

                assert cli.run_list(args) == 0
                captured = capsys.readouterr()
                data = json.loads(captured.out)
                assert data["status"] == "success"
                assert data["total_profiles"] == 1
                assert data["total_bytes"] == 1048576
                assert data["browsers"] == matches


def test_run_list_json_empty(capsys: pytest.CaptureFixture) -> None:
    """Verify run_list outputs no_browsers_found JSON when empty."""
    args = argparse.Namespace(json=True, quiet=False, list=True, browser=None)
    with patch("atlas.lib.browsers.verify_entries", return_value=True):
        with patch("atlas.lib.permissions.is_elevated", return_value=False):
            with patch("atlas.cli.Pipeline") as mock_pipeline_cls:
                mock_inst = MagicMock()
                mock_inst.browsers = {"Firefox": {}}
                mock_inst.scan_profiles.return_value = {}
                mock_pipeline_cls.return_value = mock_inst

                assert cli.run_list(args) == 0
                captured = capsys.readouterr()
                data = json.loads(captured.out)
                assert data["status"] == "no_browsers_found"
                assert data["browsers"] == {}


def test_run_list_json_unknown_browser(capsys: pytest.CaptureFixture) -> None:
    """Verify run_list outputs JSON error for unknown browser."""
    args = argparse.Namespace(
        json=True, quiet=False, list=True, browser="unknown"
    )
    with patch("atlas.lib.browsers.verify_entries", return_value=True):
        with patch("atlas.lib.permissions.is_elevated", return_value=False):
            with patch("atlas.cli.Pipeline") as mock_pipeline_cls:
                mock_inst = MagicMock()
                mock_inst.browsers = {}
                mock_pipeline_cls.return_value = mock_inst

                assert cli.run_list(args) == 1
                captured = capsys.readouterr()
                data = json.loads(captured.out)
                assert data["status"] == "error"
                assert "No browser found" in data["message"]


def test_run_backup_json(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    """Verify run_backup outputs structured JSON summary."""
    arc_file = tmp_path / "Firefox.zip"
    arc_file.write_bytes(b"PK\x05\x06" + b"\x00" * 18)
    args = argparse.Namespace(
        json=True,
        verify=False,
        quiet=False,
        list=False,
        browser=None,
        output=None,
    )
    with patch("atlas.lib.browsers.verify_entries", return_value=True):
        with patch("atlas.lib.permissions.is_elevated", return_value=False):
            with patch("atlas.cli.Pipeline") as mock_pipeline_cls:
                mock_inst = MagicMock()
                mock_inst.browsers = {"Firefox": {}}
                mock_inst.run.return_value = PipelineResult.SUCCESS
                mock_inst.created_archives = [arc_file]
                mock_pipeline_cls.return_value = mock_inst

                assert cli.run_backup(args) == 0
                captured = capsys.readouterr()
                data = json.loads(captured.out)
                assert data["status"] == "success"
                assert data["total_archives"] == 1
                assert data["archives"][0]["name"] == "Firefox.zip"


def test_run_backup_verify_success(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    """Verify run_backup with -C/--verify succeeds on valid archive."""
    arc_file = tmp_path / "Firefox.zip"
    arc_file.write_bytes(b"content")
    args = argparse.Namespace(
        json=False,
        verify=True,
        quiet=False,
        list=False,
        browser=None,
        output=None,
    )
    with patch("atlas.lib.browsers.verify_entries", return_value=True):
        with patch("atlas.lib.permissions.is_elevated", return_value=False):
            with patch("atlas.cli.Pipeline") as mock_pipeline_cls:
                mock_inst = MagicMock()
                mock_inst.browsers = {"Firefox": {}}
                mock_inst.run.return_value = PipelineResult.SUCCESS
                mock_inst.created_archives = [arc_file]
                mock_pipeline_cls.return_value = mock_inst

                with patch(
                    "atlas.backup.archive.verify_archive",
                    return_value=(True, None, 5),
                ):
                    assert cli.run_backup(args) == 0
                    captured = capsys.readouterr()
                    assert "[Verify] Firefox.zip: OK" in captured.out
                    assert "Backup completed successfully." in captured.out


def test_run_backup_verify_failure(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    """Verify run_backup with -C/--verify fails when archive is corrupt."""
    arc_file = tmp_path / "Corrupt.zip"
    arc_file.write_bytes(b"bad")
    args = argparse.Namespace(
        json=False,
        verify=True,
        quiet=False,
        list=False,
        browser=None,
        output=None,
    )
    with patch("atlas.lib.browsers.verify_entries", return_value=True):
        with patch("atlas.lib.permissions.is_elevated", return_value=False):
            with patch("atlas.cli.Pipeline") as mock_pipeline_cls:
                mock_inst = MagicMock()
                mock_inst.browsers = {"Firefox": {}}
                mock_inst.run.return_value = PipelineResult.SUCCESS
                mock_inst.created_archives = [arc_file]
                mock_pipeline_cls.return_value = mock_inst

                with patch(
                    "atlas.backup.archive.verify_archive",
                    return_value=(False, "Bad CRC-32", 1),
                ):
                    assert cli.run_backup(args) == 1
                    captured = capsys.readouterr()
                    assert "[Verify] Corrupt.zip: FAILED" in (
                        captured.out + captured.err
                    )


def test_run_backup_json_with_verify(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    """Verify run_backup with --json and --verify includes verify status."""
    arc_file = tmp_path / "Firefox.zip"
    arc_file.write_bytes(b"zipdata")
    args = argparse.Namespace(
        json=True,
        verify=True,
        quiet=False,
        list=False,
        browser=None,
        output=None,
    )
    with patch("atlas.lib.browsers.verify_entries", return_value=True):
        with patch("atlas.lib.permissions.is_elevated", return_value=False):
            with patch("atlas.cli.Pipeline") as mock_pipeline_cls:
                mock_inst = MagicMock()
                mock_inst.browsers = {"Firefox": {}}
                mock_inst.run.return_value = PipelineResult.SUCCESS
                mock_inst.created_archives = [arc_file]
                mock_pipeline_cls.return_value = mock_inst

                with patch(
                    "atlas.backup.archive.verify_archive",
                    return_value=(True, None, 10),
                ):
                    assert cli.run_backup(args) == 0
                    captured = capsys.readouterr()
                    data = json.loads(captured.out)
                    assert data["status"] == "success"
                    assert data["archives"][0]["verified"] is True
                    assert data["archives"][0]["file_count"] == 10


def test_run_backup_json_with_verify_failure(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    """Verify run_backup with --json and verify failure returns code 1."""
    arc_file = tmp_path / "Firefox.zip"
    arc_file.write_bytes(b"badzip")
    args = argparse.Namespace(
        json=True,
        verify=True,
        quiet=False,
        list=False,
        browser=None,
        output=None,
    )
    with patch("atlas.lib.browsers.verify_entries", return_value=True):
        with patch("atlas.lib.permissions.is_elevated", return_value=False):
            with patch("atlas.cli.Pipeline") as mock_pipeline_cls:
                mock_inst = MagicMock()
                mock_inst.browsers = {"Firefox": {}}
                mock_inst.run.return_value = PipelineResult.SUCCESS
                mock_inst.created_archives = [arc_file]
                mock_pipeline_cls.return_value = mock_inst

                with patch(
                    "atlas.backup.archive.verify_archive",
                    return_value=(False, "CRC mismatch", 3),
                ):
                    assert cli.run_backup(args) == 1
                    captured = capsys.readouterr()
                    data = json.loads(captured.out)
                    assert data["status"] == "verification_failed"
                    assert data["archives"][0]["verified"] is False
                    assert data["archives"][0]["error"] == "CRC mismatch"


def test_run_list_scan_unexpected_exception(
    capsys: pytest.CaptureFixture,
) -> None:
    """Verify run_list catches unexpected scan exception safely."""
    args = argparse.Namespace(
        list=True, quiet=False, json=False, browser=None
    )
    with patch("atlas.lib.browsers.verify_entries", return_value=True):
        with patch("atlas.lib.permissions.is_elevated", return_value=False):
            with patch("atlas.cli.Pipeline") as mock_pipeline_cls:
                mock_inst = MagicMock()
                mock_inst.browsers = {"Firefox": {}}
                mock_inst.scan_profiles.side_effect = RuntimeError("I/O error")
                mock_pipeline_cls.return_value = mock_inst

                assert cli.run_list(args) == 1
                captured = capsys.readouterr()
                assert "unexpected error occurred during scan" in captured.out


def test_run_list_size_unexpected_exception(
    capsys: pytest.CaptureFixture,
) -> None:
    """Verify run_list catches unexpected size estimation exception safely."""
    args = argparse.Namespace(
        list=True, quiet=False, json=False, browser=None
    )
    with patch("atlas.lib.browsers.verify_entries", return_value=True):
        with patch("atlas.lib.permissions.is_elevated", return_value=False):
            with patch("atlas.cli.Pipeline") as mock_pipeline_cls:
                mock_inst = MagicMock()
                mock_inst.browsers = {"Firefox": {}}
                mock_inst.scan_profiles.return_value = {"Firefox": ["/p"]}
                mock_inst.estimate_size.side_effect = OSError("Access denied")
                mock_pipeline_cls.return_value = mock_inst

                assert cli.run_list(args) == 1
                captured = capsys.readouterr()
                assert (
                    "unexpected error occurred during sizing" in captured.out
                )


def test_emit_backup_json_oserror_on_stat(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    """Verify _emit_backup_json tolerates stat OSError on missing file."""
    ghost_file = tmp_path / "ghost.zip"
    cli._emit_backup_json([ghost_file], status="success")
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["status"] == "success"
    assert data["archives"][0]["size_bytes"] == 0
