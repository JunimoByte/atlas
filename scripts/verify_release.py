"""Atlas | Pre-flight Release Verification Script.

Validates that repository state, configs, tests, linters, and versioning
are consistent and release-ready before tagging a release.
"""

# =============================================================================
# IMPORTS
# =============================================================================

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# =============================================================================
# CONSTANTS & TERMINAL STYLING
# =============================================================================

SEMVER_PATTERN = re.compile(
    r"^\d+\.\d+(?:\.\d+)?(?:[a-zA-Z0-9.-]+)?$"
)

# Initialize VT processing on Windows consoles if available
if os.name == "nt":
    os.system("")

USE_COLOR = sys.stdout.isatty()

COLOR_GREEN = "\033[92m" if USE_COLOR else ""
COLOR_RED = "\033[91m" if USE_COLOR else ""
COLOR_YELLOW = "\033[93m" if USE_COLOR else ""
COLOR_CYAN = "\033[96m" if USE_COLOR else ""
COLOR_BOLD = "\033[1m" if USE_COLOR else ""
COLOR_RESET = "\033[0m" if USE_COLOR else ""


def _style(text: str, color: str) -> str:
    """Wrap text in terminal color styling."""
    return f"{color}{text}{COLOR_RESET}" if color else text


def _print_status(ok: bool, msg: str) -> None:
    """Print a formatted status line."""
    tag = _style("[OK]", COLOR_GREEN) if ok else _style("[FAIL]", COLOR_RED)
    print(f"  {tag} {msg}")


# =============================================================================
# INDIVIDUAL PRE-FLIGHT CHECKS
# =============================================================================


def check_git_status(
    repo_root: Path, allow_dirty: bool
) -> Tuple[bool, str]:
    """Verify that git working tree is clean."""
    try:
        proc = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return True, "git command not found; skipping working tree check"

    if proc.returncode != 0:
        return True, "not a git repository; skipping working tree check"

    changes = [
        line.strip()
        for line in proc.stdout.strip().splitlines()
        if line.strip()
    ]

    if not changes:
        return True, "Working directory is clean"

    if allow_dirty:
        return True, (
            f"Working directory has {len(changes)} uncommitted change(s) "
            "(bypassed via --allow-dirty)"
        )

    preview = "\n    ".join(changes[:8])
    if len(changes) > 8:
        preview += f"\n    ... and {len(changes) - 8} more"

    return False, (
        f"Working directory has {len(changes)} uncommitted changes:\n"
        f"    {preview}\n"
        "    (Commit your changes or pass --allow-dirty to ignore)"
    )


def check_version(repo_root: Path) -> Tuple[bool, str, Optional[str]]:
    """Validate pyproject.toml version format and sync with atlas.args."""
    pyproject_file = repo_root / "pyproject.toml"
    if not pyproject_file.is_file():
        return False, "pyproject.toml not found", None

    content = pyproject_file.read_text(encoding="utf-8")
    match = re.search(
        r'^\s*version\s*=\s*["\']([^"\']+)["\']', content, re.MULTILINE
    )
    if not match:
        return False, "version field not found in pyproject.toml", None

    version = match.group(1).strip()
    if not SEMVER_PATTERN.match(version):
        return (
            False,
            f"Invalid version format '{version}' in pyproject.toml",
            None,
        )

    # Cross-check that atlas.args resolves to the identical version
    proc = subprocess.run(
        [
            sys.executable,
            "-c",
            "import os, sys; sys.path.insert(0, 'src'); "
            "from atlas.args import VERSION; print(VERSION)",
        ],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=False,
    )

    if proc.returncode != 0:
        return (
            False,
            f"Failed to load atlas.args.VERSION:\n{proc.stderr.strip()}",
            version,
        )

    args_version = proc.stdout.strip()
    if args_version != version:
        return (
            False,
            f"Version mismatch: pyproject.toml ({version}) != "
            f"atlas.args.VERSION ({args_version})",
            version,
        )

    return True, f"Version format '{version}' is valid and unified", version


def _validate_entry(
    name: str, plat: str, idx: int, entry: Dict
) -> Tuple[bool, str]:
    """Validate a single browser configuration entry."""
    if not isinstance(entry, dict):
        return False, f"{name} ({plat}) entry [{idx}] must be a dict"
    if "Path" not in entry or "Type" not in entry:
        return (
            False,
            f"{name} ({plat}) entry [{idx}] missing 'Path' or 'Type'",
        )
    sig = entry.get("Signature")
    if sig is not False and not isinstance(sig, list):
        return (
            False,
            f"{name} ({plat}) entry [{idx}] "
            "'Signature' must be false or a list",
        )
    return True, "ok"


def _validate_browser_schema(browsers: Dict) -> Tuple[bool, str]:
    """Validate structural schema of browsers.json definitions."""
    for name, platforms in browsers.items():
        if not isinstance(platforms, dict):
            return False, f"Browser {name} entries must be dictionaries"
        for plat, entries in platforms.items():
            if not isinstance(entries, list):
                return False, f"{name} ({plat}) must be a list of entries"
            for idx, entry in enumerate(entries):
                ok, err = _validate_entry(name, plat, idx, entry)
                if not ok:
                    return False, err
    return True, "ok"


def check_json_configs(repo_root: Path) -> Tuple[bool, str]:
    """Validate all JSON files in configs/ for valid syntax and schemas."""
    configs_dir = repo_root / "configs"
    if not configs_dir.is_dir():
        return False, "configs/ directory not found"

    json_files = list(configs_dir.glob("*.json"))
    if not json_files:
        return False, "No JSON configuration files found in configs/"

    for json_file in json_files:
        try:
            data = json.loads(json_file.read_text(encoding="utf-8"))
        except Exception as exc:
            return False, f"Malformed JSON in {json_file.name}: {exc}"

        if not isinstance(data, dict):
            return False, f"{json_file.name} root must be a JSON object"

        if json_file.name == "browsers.json":
            valid, err = _validate_browser_schema(data)
            if not valid:
                return False, err

    return True, f"All {len(json_files)} JSON configs are valid"


def check_inno_setup(
    repo_root: Path, expected_version: str
) -> Tuple[bool, str]:
    """Verify that Inno Setup (installer/Atlas.iss) resolves the version."""
    iss_file = repo_root / "installer" / "Atlas.iss"
    if not iss_file.is_file():
        return False, "installer/Atlas.iss not found"

    # Run the exact resolution command used by Atlas.iss
    proc = subprocess.run(
        [
            sys.executable,
            "-c",
            "import os, sys; sys.path.insert(0, os.path.abspath('../src')); "
            "from atlas.args import VERSION; print(VERSION)",
        ],
        cwd=str(repo_root / "installer"),
        capture_output=True,
        text=True,
        check=False,
    )

    if proc.returncode != 0:
        return (
            False,
            f"Atlas.iss version script failed:\n{proc.stderr.strip()}",
        )

    resolved = proc.stdout.strip()
    if resolved != expected_version:
        return (
            False,
            f"Atlas.iss resolved version '{resolved}', "
            f"expected '{expected_version}'",
        )

    return True, f"Atlas.iss resolves version '{resolved}' cleanly"


def check_ruff(repo_root: Path) -> Tuple[bool, str]:
    """Execute ruff linter if installed in current Python environment."""
    proc = subprocess.run(
        [sys.executable, "-m", "ruff", "check", "."],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=False,
    )

    if proc.returncode != 0 and "No module named ruff" in proc.stderr:
        return True, "ruff is not installed in environment (skipped)"

    if proc.returncode != 0:
        out = proc.stdout.strip() or proc.stderr.strip()
        return False, f"Ruff reported lint errors:\n    {out}"

    return True, "Ruff linting passed cleanly"


def check_flake8(repo_root: Path) -> Tuple[bool, str]:
    """Execute flake8 linter if installed in current Python environment."""
    proc = subprocess.run(
        [sys.executable, "-m", "flake8", "."],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=False,
    )

    if proc.returncode != 0 and "No module named flake8" in proc.stderr:
        return True, "flake8 is not installed in environment (skipped)"

    if proc.returncode != 0:
        out = proc.stdout.strip() or proc.stderr.strip()
        return False, f"Flake8 reported lint errors:\n    {out}"

    return True, "Flake8 linting passed cleanly"


def check_pytest(repo_root: Path) -> Tuple[bool, str]:
    """Execute pytest unit test suite."""
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=False,
    )

    if proc.returncode != 0 and "No module named pytest" in proc.stderr:
        return False, "pytest is not installed in current Python environment"

    if proc.returncode != 0:
        out = proc.stdout.strip() or proc.stderr.strip()
        lines = out.splitlines()
        tail = "\n    ".join(lines[-5:]) if lines else "Unknown error"
        return False, f"Pytest test suite failed:\n    {tail}"

    # Extract test count summary line (e.g. '480 passed in 1.18s')
    summary = "all tests passed"
    lines = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    if lines:
        summary = lines[-1].strip("=")

    return True, f"Pytest suite passed ({summary})"


# =============================================================================
# RUNNER
# =============================================================================


def _run_linters(repo_root: Path, failures: List[str]) -> None:
    """Run ruff and flake8 linters and append failures."""
    for _name, check_fn in [
        ("Ruff", check_ruff),
        ("Flake8", check_flake8),
    ]:
        ok, msg = check_fn(repo_root)
        _print_status(ok, msg)
        if not ok:
            failures.append(msg)


def main() -> int:
    """Execute pre-flight release checks and return status code."""
    parser = argparse.ArgumentParser(
        description="Atlas 1-Command Pre-Flight Release Check"
    )
    parser.add_argument(
        "--allow-dirty",
        action="store_true",
        help="Permit uncommitted changes in git working tree",
    )
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="Skip running pytest unit test suite",
    )
    parser.add_argument(
        "--skip-lint",
        action="store_true",
        help="Skip running ruff and flake8 linters",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent

    banner_title = "\n=== Atlas Pre-Flight Release Verification ==="
    print(_style(banner_title, COLOR_BOLD))
    print(f"Target repository: {repo_root}\n")

    failures: List[str] = []

    # 1. Git Working Directory
    ok, msg = check_git_status(repo_root, args.allow_dirty)
    _print_status(ok, msg)
    if not ok:
        failures.append(msg)

    # 2. Version Format & Synchronization
    ok, msg, version = check_version(repo_root)
    _print_status(ok, msg)
    if not ok:
        failures.append(msg)
        version = "unknown"

    # 3. JSON Configuration Integrity
    ok, msg = check_json_configs(repo_root)
    _print_status(ok, msg)
    if not ok:
        failures.append(msg)

    # 4. Inno Setup (Atlas.iss) Version Resolution
    ok, msg = check_inno_setup(repo_root, version or "")
    _print_status(ok, msg)
    if not ok:
        failures.append(msg)

    # 5. Linters
    if not args.skip_lint:
        _run_linters(repo_root, failures)
    else:
        print(f"  {_style('[SKIP]', COLOR_YELLOW)} Linters skipped via flag")

    # 6. Pytest
    if not args.skip_tests:
        ok, msg = check_pytest(repo_root)
        _print_status(ok, msg)
        if not ok:
            failures.append(msg)
    else:
        print(f"  {_style('[SKIP]', COLOR_YELLOW)} Tests skipped via flag")

    # Final Summary
    print()
    if not failures:
        banner = f"[OK] All checks passed. Atlas v{version} is ready to tag."
        border = "=" * len(banner)
        print(_style(border, COLOR_GREEN))
        print(_style(banner, COLOR_GREEN + COLOR_BOLD))
        print(_style(border, COLOR_GREEN))
        print("\nNext steps to publish release:")
        print(f"  git tag v{version}")
        print(f"  git push origin v{version}\n")
        return 0

    banner = "[FAIL] Pre-flight release checks failed."
    border = "=" * len(banner)
    print(_style(border, COLOR_RED))
    print(_style(banner, COLOR_RED + COLOR_BOLD))
    print(_style(border, COLOR_RED))
    print(f"\nPlease resolve the {len(failures)} issue(s) above.\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())
