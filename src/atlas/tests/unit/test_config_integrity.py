"""Atlas | Tests | Config Integrity.

Validates the syntax and schemas of all production configuration files in
the configs/ directory (browsers.json, blacklist.json).
"""

# =============================================================================
# IMPORTS
# =============================================================================

import json
from pathlib import Path
from typing import Any, Dict

import pytest

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture(scope="session")
def configs_dir() -> Path:
    """Return the absolute path to the project's configs directory."""
    repo_root = Path(__file__).resolve().parents[4]
    dir_path = repo_root / "configs"
    assert dir_path.is_dir(), f"Configs directory not found at {dir_path}"
    return dir_path


# =============================================================================
# TESTS
# =============================================================================


def test_all_configs_valid_json(configs_dir: Path) -> None:
    """Ensure every JSON file in the configs directory parses without error."""
    json_files = list(configs_dir.glob("*.json"))
    assert json_files, "No JSON config files found in configs/"

    for json_file in json_files:
        content = json_file.read_text(encoding="utf-8")
        parsed = json.loads(content)
        assert isinstance(parsed, dict), (
            f"{json_file.name} root must be a JSON object (dict)"
        )


def test_browsers_config_schema(configs_dir: Path) -> None:
    """Validate schema and required fields across all browser definitions.

    Verifies that:
    - Every browser definition maps to platform keys (e.g. Windows, Linux).
    - Every entry specifies non-empty 'Path' and 'Type'.
    - 'Signature' is either a list of string file markers or boolean False
      for profiles that do not require file signature matching.
    """
    browsers_file = configs_dir / "browsers.json"
    assert browsers_file.is_file(), "configs/browsers.json missing"

    data: Dict[str, Any] = json.loads(
        browsers_file.read_text(encoding="utf-8")
    )
    assert len(data) > 0, "configs/browsers.json contains no browsers"

    for browser_name, platforms in data.items():
        assert isinstance(platforms, dict), (
            f"Browser '{browser_name}' must map to a dictionary of platforms."
        )

        for platform_name, entries in platforms.items():
            assert isinstance(entries, list), (
                f"Platform '{platform_name}' under '{browser_name}' "
                "must be a list of configuration entries."
            )

            seen_pairs = set()
            for index, entry in enumerate(entries):
                location_str = (
                    f"{browser_name} -> {platform_name} -> entry [{index}]"
                )
                assert isinstance(entry, dict), (
                    f"Entry at {location_str} must be a dictionary."
                )

                # Required keys
                assert "Path" in entry, f"Missing 'Path' at {location_str}"
                assert "Type" in entry, f"Missing 'Type' at {location_str}"
                assert "Signature" in entry, (
                    f"Missing 'Signature' at {location_str}"
                )

                # Field types & values
                path_val = entry["Path"]
                assert (
                    isinstance(path_val, str) and path_val.strip()
                ), f"Empty or non-string 'Path' at {location_str}"
                assert path_val == path_val.strip(), (
                    f"Untrimmed whitespace in 'Path' at {location_str}"
                )

                type_val = entry["Type"]
                assert (
                    isinstance(type_val, str) and type_val.strip()
                ), f"Empty or non-string 'Type' at {location_str}"
                assert type_val == type_val.strip(), (
                    f"Untrimmed whitespace in 'Type' at {location_str}"
                )

                pair = (path_val, type_val)
                assert pair not in seen_pairs, (
                    f"Duplicate (Path, Type) pair {pair} at {location_str}"
                )
                seen_pairs.add(pair)

                sig = entry["Signature"]
                assert sig is False or (
                    isinstance(sig, list)
                    and all(isinstance(s, str) and s for s in sig)
                ), (
                    f"Invalid 'Signature' at {location_str}: "
                    "expected list of strings or boolean False."
                )


def test_blacklist_config_schema(configs_dir: Path) -> None:
    """Validate structure and data types of configs/blacklist.json."""
    blacklist_file = configs_dir / "blacklist.json"
    assert blacklist_file.is_file(), "configs/blacklist.json missing"

    data: Dict[str, Any] = json.loads(
        blacklist_file.read_text(encoding="utf-8")
    )

    required_keys = (
        "SKIP_FILE_EXTENSION",
        "SKIP_FOLDERS",
        "SKIP_FILE_WITH_EXTENSION",
    )
    for key in required_keys:
        assert key in data, f"Missing required key '{key}' in blacklist.json"

    # Validate file extension exclusions
    ext_list = data["SKIP_FILE_EXTENSION"]
    assert isinstance(ext_list, list) and len(ext_list) > 0
    assert all(
        isinstance(ext, str) and ext.startswith(".") for ext in ext_list
    )

    # Validate folder exclusions
    folder_list = data["SKIP_FOLDERS"]
    assert isinstance(folder_list, list) and len(folder_list) > 0
    assert all(
        isinstance(folder, str) and folder.strip() for folder in folder_list
    )

    # Ensure no duplicate entries in any list
    assert len(ext_list) == len(set(ext_list)), (
        "Duplicate entries in SKIP_FILE_EXTENSION: "
        + str([e for e in ext_list if ext_list.count(e) > 1])
    )
    assert len(folder_list) == len(set(folder_list)), (
        "Duplicate entries in SKIP_FOLDERS: "
        + str([f for f in folder_list if folder_list.count(f) > 1])
    )

    # Validate conditional extension exclusions
    ext_dict = data["SKIP_FILE_WITH_EXTENSION"]
    assert isinstance(ext_dict, dict)
    for ext, filenames in ext_dict.items():
        assert isinstance(ext, str) and ext.startswith(".")
        assert isinstance(filenames, list) and len(filenames) > 0
        assert all(
            isinstance(fn, str) and fn.strip() for fn in filenames
        )


def test_types_config_schema(configs_dir: Path) -> None:
    """Validate structure and data types of configs/types.json."""
    types_file = configs_dir / "types.json"
    assert types_file.is_file(), "configs/types.json missing"

    data: Dict[str, Any] = json.loads(
        types_file.read_text(encoding="utf-8")
    )
    assert isinstance(data, dict) and len(data) > 0, (
        "types.json must be a non-empty JSON object"
    )
