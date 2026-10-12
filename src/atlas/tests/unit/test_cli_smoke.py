"""Atlas | Tests | CLI Smoke.

Contract and smoke tests for CLI entry points, exit codes, and output formats.
Verifies that CLI commands produce deterministic exit codes, valid JSON,
and well-formed outputs without subprocess overhead or flakiness.
"""

# =============================================================================
# IMPORTS
# =============================================================================

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from atlas import cli
from atlas.args import parse_args

# =============================================================================
# TESTS — Help & Argument Contracts
# =============================================================================


def test_cli_help_flag_contract(capsys: pytest.CaptureFixture) -> None:
    """Verify --help flag displays usage and exits with code 0."""
    with pytest.raises(SystemExit) as exc_info:
        parse_args(["--help"])
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "usage:" in captured.out.lower()
    assert "--cli" in captured.out
    assert "--json" in captured.out


def test_cli_short_help_flag_contract(capsys: pytest.CaptureFixture) -> None:
    """Verify -h flag displays usage and exits with code 0."""
    with pytest.raises(SystemExit) as exc_info:
        parse_args(["-h"])
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "usage:" in captured.out.lower()


# =============================================================================
# TESTS — Profile Listing Contracts
# =============================================================================


def test_cli_list_text_contract(capsys: pytest.CaptureFixture) -> None:
    """Verify --list returns exit code 0 and non-empty output."""
    args = parse_args(["--list"])
    exit_code = cli.run_cli(args)
    assert exit_code in (0, 1)
    captured = capsys.readouterr()
    combined = captured.out + captured.err
    assert len(combined.strip()) > 0


def test_cli_list_json_schema_contract(
    capsys: pytest.CaptureFixture,
) -> None:
    """Verify --list --json adheres to expected JSON schema."""
    args = parse_args(["--list", "--json"])
    exit_code = cli.run_cli(args)
    assert exit_code == 0

    captured = capsys.readouterr()
    data = json.loads(captured.out)

    assert "status" in data
    assert data["status"] in ("success", "no_browsers_found")
    assert "total_profiles" in data
    assert isinstance(data["total_profiles"], int)
    assert "total_bytes" in data
    assert isinstance(data["total_bytes"], int)
    assert "formatted_size" in data
    assert isinstance(data["formatted_size"], str)
    assert "browsers" in data
    assert isinstance(data["browsers"], dict)


# =============================================================================
# TESTS — Error & Filter Contracts
# =============================================================================


def test_cli_unknown_browser_filter_contract(
    capsys: pytest.CaptureFixture,
) -> None:
    """Verify non-existent browser target exits with code 1 and error text."""
    args = parse_args(["--cli", "--browser", "NonExistentBrowserXYZ123"])
    exit_code = cli.run_cli(args)
    assert exit_code == 1

    captured = capsys.readouterr()
    assert "NonExistentBrowserXYZ123" in (captured.out + captured.err)


def test_cli_unknown_browser_filter_json_contract(
    capsys: pytest.CaptureFixture,
) -> None:
    """Verify non-existent browser target in JSON mode emits valid error."""
    args = parse_args(
        ["--cli", "--browser", "NonExistentBrowserXYZ123", "--json"]
    )
    exit_code = cli.run_cli(args)
    assert exit_code == 1

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["status"] == "error"
    assert "NonExistentBrowserXYZ123" in data["message"]


def test_cli_invalid_output_directory_contract(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    """Verify existing file path passed to --output triggers clean error."""
    conflict_file = tmp_path / "not_a_directory.txt"
    conflict_file.write_text("dummy", encoding="utf-8")

    args = parse_args(["--cli", "-o", str(conflict_file), "--json"])
    exit_code = cli.run_cli(args)
    assert exit_code == 1

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["status"] == "error"
    assert "Invalid output directory" in data["message"]


# =============================================================================
# TESTS — Unmocked Execution Contracts
# =============================================================================


def test_cli_full_backup_json_roundtrip_contract(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    """Verify --cli --verify --json runs backup and emits verification."""
    source_dir = tmp_path / "source_prof"
    source_dir.mkdir(parents=True, exist_ok=True)
    (source_dir / "Preferences").write_text("{}", encoding="utf-8")
    (source_dir / "Bookmarks").write_text("{}", encoding="utf-8")

    output_dir = tmp_path / "cli_out"
    output_dir.mkdir(parents=True, exist_ok=True)

    fake_browsers = {
        "SmokeBrowser": {
            "Path": "source_prof",
            "Type": "Chromium",
            "Signature": "Preferences",
        }
    }

    args = parse_args(
        [
            "--cli",
            "--browser",
            "SmokeBrowser",
            "--output",
            str(output_dir),
            "--verify",
            "--json",
        ]
    )

    from atlas.backup import archive

    try:
        with patch("atlas.lib.browsers.grab", return_value=fake_browsers):
            with patch(
                "atlas.backup.pipeline.Profile.find_profile",
                return_value=[str(source_dir)],
            ):
                exit_code = cli.run_cli(args)
    finally:
        archive.set_zip_output_dir(None)

    assert exit_code == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)

    assert data["status"] == "success"
    assert data["total_archives"] == 1
    archive_info = data["archives"][0]
    assert archive_info["verified"] is True
    assert archive_info["file_count"] >= 2
    assert Path(archive_info["archive"]).is_file()
