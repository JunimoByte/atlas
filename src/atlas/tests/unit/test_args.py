"""Atlas | Tests | Args.

Unit tests for args.py covering parser construction, flags, defaults,
version reporting, known argument handling, and non-Windows safety edge cases.
"""

# =============================================================================
# IMPORTS
# =============================================================================

from pathlib import Path
from typing import Generator

import pytest

from atlas import args

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture(autouse=True)
def reset_cached_version() -> Generator[None, None, None]:
    """Ensure _CACHED_VERSION is reset before and after every test."""
    args._CACHED_VERSION = None
    yield
    args._CACHED_VERSION = None


# =============================================================================
# TESTS — Version Resolution & Caching
# =============================================================================


def test_get_version() -> None:
    """Verify get_version extracts semantic version from pyproject.toml."""
    version = args.get_version(force_refresh=True)
    assert isinstance(version, str)
    assert version == "1.2"


def test_get_version_caching(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify get_version caches the result and reuses it without probing."""
    args._CACHED_VERSION = "9.9.9"
    assert args.get_version() == "9.9.9"
    # force_refresh bypasses cache
    assert args.get_version(force_refresh=True) != "9.9.9"


def test_get_version_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify get_version falls back cleanly when files are missing."""
    monkeypatch.setattr(Path, "is_file", lambda self: False)
    monkeypatch.setattr(
        args, "_extract_version_from_file", lambda path: None
    )
    assert isinstance(args.get_version(force_refresh=True), str)


def test_extract_version_from_file(tmp_path: Path) -> None:
    """Verify _extract_version_from_file handles BOM, comments, and tables."""
    toml = tmp_path / "pyproject.toml"

    # 1. Normal project section
    toml.write_text(
        '[project]\nname = "test"\nversion = "2.3.4"\n',
        encoding="utf-8-sig",
    )
    assert args._extract_version_from_file(toml) == "2.3.4"

    # 2. Key inside another table should NOT match project version
    toml.write_text(
        '[tool.poetry]\nname = "test"\n[other]\nversion = "0.0.1"\n',
        encoding="utf-8",
    )
    assert args._extract_version_from_file(toml) is None

    # 3. Non-existent file returns None
    assert args._extract_version_from_file(tmp_path / "missing.toml") is None


# =============================================================================
# TESTS — Cross-Platform Path Handling
# =============================================================================


def test_source_toml_paths_shallow_filesystem(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify shallow paths (e.g. root mounts) do not raise IndexError."""
    mock_file = Path("/args.py")
    monkeypatch.setattr(args, "__file__", str(mock_file))
    paths = args._get_candidate_toml_paths()
    assert isinstance(paths, list)


def test_candidate_paths_ignores_cwd(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Verify candidate paths do not include cwd or get hijacked by it."""
    alien_toml = tmp_path / "pyproject.toml"
    alien_toml.write_text('[project]\nversion = "99.9.9"\n')
    monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
    paths = args._get_candidate_toml_paths()
    assert alien_toml not in paths


def test_frozen_toml_paths_appimage_and_meipass(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Verify AppImage and PyInstaller candidates are discovered."""
    monkeypatch.setattr(
        args.sys, "_MEIPASS", str(tmp_path / "meipass"), raising=False
    )
    monkeypatch.setenv("APPDIR", str(tmp_path / "appdir"))

    candidates = args._get_candidate_toml_paths()
    paths_str = [str(p) for p in candidates]
    assert any("meipass" in p for p in paths_str)
    assert any("appdir" in p for p in paths_str)


# =============================================================================
# TESTS — Parser & Flag Handling
# =============================================================================


def test_build_parser_options() -> None:
    """Verify build_parser configures expected CLI flags."""
    parser = args.build_parser()
    actions = {action.dest for action in parser._actions}
    assert "cli" in actions
    assert "output" in actions
    assert "help" in actions


def test_parse_args_defaults() -> None:
    """Verify default arguments when none are passed."""
    parsed = args.parse_args([])
    assert parsed.cli is False
    assert parsed.output is None


def test_parse_args_output_short() -> None:
    """Verify -o flag sets custom output directory."""
    parsed = args.parse_args(["-o", "/tmp/backup"])
    assert parsed.output == "/tmp/backup"


def test_parse_args_output_long() -> None:
    """Verify --output flag sets custom output directory."""
    parsed = args.parse_args(["--output", "/tmp/backup"])
    assert parsed.output == "/tmp/backup"


def test_parse_args_cli_flag() -> None:
    """Verify --cli flag enables CLI mode."""
    parsed = args.parse_args(["--cli"])
    assert parsed.cli is True


def test_parse_args_ignores_unknown_flags() -> None:
    """Verify parse_args tolerates unknown options gracefully."""
    parsed = args.parse_args(["--unknown-option", "--cli"])
    assert parsed.cli is True


def test_parse_args_version_long(capsys: pytest.CaptureFixture) -> None:
    """Verify --version prints version string and exits cleanly."""
    with pytest.raises(SystemExit) as exc_info:
        args.parse_args(["--version"])
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    expected = f"Atlas {args.VERSION}"
    assert expected in captured.out or expected in captured.err


def test_parse_args_version_short(capsys: pytest.CaptureFixture) -> None:
    """Verify -v prints version string and exits cleanly."""
    with pytest.raises(SystemExit) as exc_info:
        args.parse_args(["-v"])
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    expected = f"Atlas {args.VERSION}"
    assert expected in captured.out or expected in captured.err


def test_parse_args_embedded_runtime_sys_argv_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify parse_args defaults safely when sys.argv is None."""
    monkeypatch.setattr(args.sys, "argv", None)
    parsed = args.parse_args(None)
    assert parsed.cli is False


def test_parse_args_embedded_runtime_missing_argv(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify parse_args defaults safely when sys has no argv attribute."""
    monkeypatch.delattr(args.sys, "argv", raising=False)
    parsed = args.parse_args(None)
    assert parsed.cli is False
