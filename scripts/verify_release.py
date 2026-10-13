#!/usr/bin/env python3
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
from typing import List, Optional, Tuple

# =============================================================================
# CONSTANTS & CONFIGURATION
# =============================================================================

ROOT = Path(__file__).resolve().parent.parent
SEMVER = re.compile(r"^\d+\.\d+(?:\.\d+)?(?:[a-zA-Z0-9.-]+)?$")

if os.name == "nt":
    os.system("")

COLOR = sys.stdout.isatty()
GREEN = "\033[92m" if COLOR else ""
RED = "\033[91m" if COLOR else ""
YELLOW = "\033[93m" if COLOR else ""
BOLD = "\033[1m" if COLOR else ""
RESET = "\033[0m" if COLOR else ""


def _style(text: str, color: str) -> str:
    """Format text with ANSI escape color code."""
    return f"{color}{text}{RESET}" if color else text


def _status(ok: bool, msg: str) -> bool:
    """Print formatted check status line and return ok boolean."""
    tag = _style("[OK]", GREEN) if ok else _style("[FAIL]", RED)
    print(f"  {tag} {msg}")
    return ok


def _run(
    cmd: List[str], cwd: Optional[Path] = None
) -> subprocess.CompletedProcess:
    """Execute subprocess from repo root or specified directory."""
    return subprocess.run(
        cmd,
        cwd=str(cwd or ROOT),
        capture_output=True,
        text=True,
        check=False,
    )


# =============================================================================
# INDIVIDUAL PRE-FLIGHT CHECKS
# =============================================================================


def check_git(allow_dirty: bool) -> Tuple[bool, str]:
    """Verify that git working tree is clean."""
    res = _run(["git", "status", "--porcelain"])
    if res.returncode != 0:
        return True, "git repository not detected (skipped)"
    lines = [
        line.strip() for line in res.stdout.splitlines() if line.strip()
    ]
    if not lines:
        return True, "Working directory is clean"
    if allow_dirty:
        return (
            True,
            f"Working tree has {len(lines)} changes (bypassed via "
            "--allow-dirty)",
        )
    return (
        False,
        f"Working tree has {len(lines)} uncommitted change(s) "
        "(--allow-dirty to bypass)",
    )


def check_version() -> Tuple[bool, str, Optional[str]]:
    """Validate pyproject.toml version format and sync with atlas.args."""
    toml_path = ROOT / "pyproject.toml"
    match = re.search(
        r'^\s*version\s*=\s*["\']([^"\']+)["\']',
        toml_path.read_text(encoding="utf-8"),
        re.MULTILINE,
    )
    if not match or not SEMVER.match(match.group(1).strip()):
        return False, "Invalid or missing version in pyproject.toml", None
    version = match.group(1).strip()

    res = _run([
        sys.executable,
        "-c",
        "import sys; sys.path.insert(0, 'src'); "
        "from atlas.args import VERSION; print(VERSION)",
    ])
    if res.returncode != 0 or res.stdout.strip() != version:
        args_ver = res.stdout.strip() or "unknown"
        return (
            False,
            f"Version mismatch: pyproject.toml ({version}) != "
            f"atlas.args ({args_ver})",
            version,
        )
    return True, f"Version format '{version}' is valid and unified", version


def check_configs() -> Tuple[bool, str]:
    """Validate that all config JSON files parse cleanly."""
    json_files = list((ROOT / "configs").glob("*.json"))
    for jf in json_files:
        try:
            data = json.loads(jf.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                return False, f"{jf.name} root is not a JSON object"
        except Exception as exc:
            return False, f"Malformed JSON in {jf.name}: {exc}"
    return True, f"All {len(json_files)} JSON config files parse cleanly"


def check_iss(version: str) -> Tuple[bool, str]:
    """Verify that installer/Atlas.iss version extraction script works."""
    res = _run(
        [
            sys.executable,
            "-c",
            "import os, sys; sys.path.insert(0, os.path.abspath('../src')); "
            "from atlas.args import VERSION; print(VERSION)",
        ],
        cwd=ROOT / "installer",
    )
    if res.returncode != 0 or res.stdout.strip() != version:
        out = res.stdout.strip() or "failed"
        return (
            False,
            f"Atlas.iss resolved '{out}', expected '{version}'",
        )
    return True, f"Atlas.iss resolves version '{version}' cleanly"


def check_linter(tool: str) -> Tuple[bool, str]:
    """Execute a linter module gently, skipping if not installed."""
    cmd = (
        [sys.executable, "-m", tool, "check", "."]
        if tool == "ruff"
        else [sys.executable, "-m", tool, "."]
    )
    res = _run(cmd)
    if res.returncode != 0 and f"No module named {tool}" in res.stderr:
        return True, f"{tool} is not installed in environment (skipped)"
    if res.returncode != 0:
        err = res.stdout.strip() or res.stderr.strip()
        return False, f"{tool} reported violations:\n    {err}"
    return True, f"{tool.capitalize()} linting passed cleanly"


def check_tests() -> Tuple[bool, str]:
    """Execute the pytest test suite."""
    res = _run([sys.executable, "-m", "pytest", "-q"])
    if res.returncode != 0 and "No module named pytest" in res.stderr:
        return False, "pytest is not installed in current environment"
    if res.returncode != 0:
        tail = res.stdout.strip().splitlines()[-1] if res.stdout else "Error"
        return False, f"Pytest tests failed: {tail}"
    lines = [
        ln.strip("=") for ln in res.stdout.splitlines() if ln.strip()
    ]
    summary = lines[-1].strip() if lines else "all tests passed"
    return True, f"Pytest suite passed ({summary})"


# =============================================================================
# RUNNER
# =============================================================================


def _run_linters(skip: bool, errors: List[str]) -> None:
    """Run ruff and flake8 linters or report skip."""
    if skip:
        print(f"  {_style('[SKIP]', YELLOW)} Linters skipped via flag")
        return
    for tool in ("ruff", "flake8"):
        ok, msg = check_linter(tool)
        if not _status(ok, msg):
            errors.append(msg)


def _run_tests(skip: bool, errors: List[str]) -> None:
    """Run pytest suite or report skip."""
    if skip:
        print(f"  {_style('[SKIP]', YELLOW)} Tests skipped via flag")
        return
    ok, msg = check_tests()
    if not _status(ok, msg):
        errors.append(msg)


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

    title = "\n=== Atlas Pre-Flight Release Verification ==="
    print(_style(title, BOLD))
    print(f"Target repository: {ROOT}\n")

    errors: List[str] = []

    # 1. Git Working Directory
    ok, msg = check_git(args.allow_dirty)
    if not _status(ok, msg):
        errors.append(msg)

    # 2. Version Synchronization
    ok, msg, version = check_version()
    if not _status(ok, msg):
        errors.append(msg)
        version = "unknown"

    # 3. JSON Configuration Parsing
    ok, msg = check_configs()
    if not _status(ok, msg):
        errors.append(msg)

    # 4. Inno Setup Version Resolution
    ok, msg = check_iss(version or "")
    if not _status(ok, msg):
        errors.append(msg)

    # 5. Linters & 6. Tests
    _run_linters(args.skip_lint, errors)
    _run_tests(args.skip_tests, errors)

    print()
    if not errors:
        banner = f"[OK] All checks passed. Atlas v{version} is ready to tag."
        border = "=" * len(banner)
        print(_style(border, GREEN))
        print(_style(banner, GREEN + BOLD))
        print(_style(border, GREEN))
        print(f"\nNext: git tag v{version} && git push origin v{version}\n")
        return 0

    banner = "[FAIL] Pre-flight release checks failed."
    border = "=" * len(banner)
    print(_style(border, RED))
    print(_style(banner, RED + BOLD))
    print(_style(border, RED))
    print(f"\nPlease resolve {len(errors)} issue(s) before tagging.\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())
