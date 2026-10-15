"""Atlas | Tests | Packages | Safe JSON Loader.

Unit tests for the read.py JSON loader.
"""

# =============================================================================
# IMPORTS
# =============================================================================

import json
import os
import sys
from pathlib import Path

import pytest

from atlas.lib import read

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def sample_json_file(tmp_path: Path) -> Path:
    """Create a temporary valid JSON file for testing."""
    file_path = tmp_path / "valid.json"
    content = {"key": "value", "number": 42}
    with file_path.open("w", encoding="utf-8") as f:
        f.write(json.dumps(content))
    return file_path


@pytest.fixture
def invalid_json_file(tmp_path: Path) -> Path:
    """Create a temporary invalid JSON file (malformed)."""
    file_path = tmp_path / "invalid.json"
    with file_path.open("w", encoding="utf-8") as f:
        f.write("{invalid_json: true")
    return file_path


@pytest.fixture
def non_dict_json_file(tmp_path: Path) -> Path:
    """Create a temporary JSON file with a list instead of a dict."""
    file_path = tmp_path / "list.json"
    with file_path.open("w", encoding="utf-8") as f:
        f.write(json.dumps([1, 2, 3]))
    return file_path


@pytest.fixture
def missing_json_file(tmp_path: Path) -> Path:
    """Create a temporary missing JSON file path."""
    return tmp_path / "missing.json"


# =============================================================================
# TESTS
# =============================================================================


def test_load_json_valid_file(sample_json_file: Path) -> None:
    """Verify that valid JSON dictionaries are loaded correctly."""
    result = read.load_json(filename=str(sample_json_file), config_dir="")
    assert isinstance(result, dict)
    assert result["key"] == "value"
    assert result["number"] == 42


@pytest.mark.parametrize(
    "fixture_name",
    ["missing_json_file", "invalid_json_file", "non_dict_json_file"],
)
def test_load_json_failure_states(
    fixture_name: str, request: pytest.FixtureRequest
) -> None:
    """Verify empty dict is returned for invalid or missing files."""
    file_path = request.getfixturevalue(fixture_name)
    result = read.load_json(filename=str(file_path), config_dir="")
    assert result == {}


def test_load_json_frozen(
    monkeypatch: pytest.MonkeyPatch, sample_json_file: Path
) -> None:
    """Verify JSON loading in a frozen environment."""
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(
        sys, "_MEIPASS", os.path.dirname(str(sample_json_file)), raising=False
    )
    result = read.load_json(filename=sample_json_file.name, config_dir="")
    assert isinstance(result, dict)
    assert result["key"] == "value"


def test_load_json_uses_installed_share_config_directory(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Verify runtime configs load from the wheel's install data location."""
    config_dir = tmp_path / "share" / "atlas" / "configs"
    config_dir.mkdir(parents=True)
    (config_dir / "runtime.json").write_text(
        json.dumps({"packaged": True}), encoding="utf-8"
    )

    monkeypatch.setattr(sys, "prefix", str(tmp_path))
    monkeypatch.setattr(
        read.os.path,
        "isdir",
        lambda path: Path(path) == config_dir,
    )

    assert read.load_json("runtime.json") == {"packaged": True}


def test_load_json_uses_user_install_share_config_directory(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Verify configs load after a standard per-user pip installation."""
    config_dir = tmp_path / "share" / "atlas" / "configs"
    config_dir.mkdir(parents=True)
    (config_dir / "runtime.json").write_text(
        json.dumps({"user_install": True}), encoding="utf-8"
    )

    monkeypatch.setattr(sys, "prefix", str(tmp_path / "venv"))
    monkeypatch.setattr(read.site, "getuserbase", lambda: str(tmp_path))
    monkeypatch.setattr(
        read.os.path,
        "isdir",
        lambda path: Path(path) == config_dir,
    )

    assert read.load_json("runtime.json") == {"user_install": True}


def test_load_json_uses_data_directory_relative_to_installed_package(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Verify data files work outside the interpreter prefix."""
    install_root = tmp_path / "target"
    config_dir = install_root / "share" / "atlas" / "configs"
    config_dir.mkdir(parents=True)
    (config_dir / "runtime.json").write_text(
        json.dumps({"prefix_install": True}), encoding="utf-8"
    )

    module_file = install_root / "atlas" / "lib" / "read.py"
    module_file.parent.mkdir(parents=True)
    module_file.touch()
    monkeypatch.setattr(read, "__file__", str(module_file))
    monkeypatch.setattr(sys, "prefix", str(tmp_path / "interpreter"))
    monkeypatch.setattr(
        read.site,
        "getuserbase",
        lambda: str(tmp_path / "user"),
    )

    assert read.load_json("runtime.json") == {"prefix_install": True}


# =============================================================================
# TEST EXECUTION
# =============================================================================

if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
