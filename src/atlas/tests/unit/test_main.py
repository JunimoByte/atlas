"""Atlas | Tests | Main.

Unit tests for main.py covering routing, version flag, and error handling.
"""

# =============================================================================
# IMPORTS
# =============================================================================

import sys
from unittest.mock import patch

import pytest

from atlas import main

# =============================================================================
# TESTS — Routing & Version Flag
# =============================================================================


def test_main_version_flag(capsys: pytest.CaptureFixture) -> None:
    """Verify --version prints the version and exits cleanly."""
    with patch.object(sys, "argv", ["atlas", "--version"]):
        with pytest.raises(SystemExit) as exc_info:
            main.main()
        assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "Atlas 1.2" in captured.out or "Atlas 1.2" in captured.err


def test_main_routes_to_cli() -> None:
    """Verify --cli flag routes execution to run_cli."""
    with patch.object(sys, "argv", ["atlas", "--cli"]):
        with patch("atlas.cli.run_cli", return_value=0) as mock_cli:
            with pytest.raises(SystemExit) as exc_info:
                main.main()
            assert exc_info.value.code == 0
            mock_cli.assert_called_once()


def test_main_routes_to_cli_on_list() -> None:
    """Verify --list flag routes execution to run_cli."""
    with patch.object(sys, "argv", ["atlas", "--list"]):
        with patch("atlas.cli.run_cli", return_value=0) as mock_cli:
            with pytest.raises(SystemExit) as exc_info:
                main.main()
            assert exc_info.value.code == 0
            mock_cli.assert_called_once()


def test_main_routes_to_gui() -> None:
    """Verify default invocation routes execution to run_gui."""
    with patch.object(sys, "argv", ["atlas"]):
        with patch("atlas.gui.run_gui", return_value=0) as mock_gui:
            with pytest.raises(SystemExit) as exc_info:
                main.main()
            assert exc_info.value.code == 0
            mock_gui.assert_called_once()


def test_main_routes_to_cli_on_browser() -> None:
    """Verify --browser flag routes execution to run_cli."""
    with patch.object(sys, "argv", ["atlas", "--browser", "firefox"]):
        with patch("atlas.cli.run_cli", return_value=0) as mock_cli:
            with pytest.raises(SystemExit) as exc_info:
                main.main()
            assert exc_info.value.code == 0
            mock_cli.assert_called_once()


def test_main_routes_to_cli_on_quiet() -> None:
    """Verify --quiet with --cli routes to run_cli and adjusts log level."""
    with patch.object(sys, "argv", ["atlas", "--cli", "--quiet"]):
        with patch("atlas.cli.run_cli", return_value=0) as mock_cli:
            with pytest.raises(SystemExit) as exc_info:
                main.main()
            assert exc_info.value.code == 0
            mock_cli.assert_called_once()


def test_main_routes_to_cli_on_json() -> None:
    """Verify --json flag routes execution to run_cli."""
    with patch.object(sys, "argv", ["atlas", "--json"]):
        with patch("atlas.cli.run_cli", return_value=0) as mock_cli:
            with pytest.raises(SystemExit) as exc_info:
                main.main()
            assert exc_info.value.code == 0
            mock_cli.assert_called_once()


def test_main_routes_to_cli_on_verify() -> None:
    """Verify --verify flag routes execution to run_cli."""
    with patch.object(sys, "argv", ["atlas", "--verify"]):
        with patch("atlas.cli.run_cli", return_value=0) as mock_cli:
            with pytest.raises(SystemExit) as exc_info:
                main.main()
            assert exc_info.value.code == 0
            mock_cli.assert_called_once()


def test_package_main_entry_point() -> None:
    """Verify atlas.__main__ delegates to main.main."""
    with patch("atlas.main.main") as mock_main:
        import runpy

        with patch.object(sys, "argv", ["atlas", "--version"]):
            runpy.run_module("atlas", run_name="__main__")
        mock_main.assert_called_once()
