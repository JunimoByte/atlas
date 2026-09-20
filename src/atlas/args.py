"""Atlas | Command-Line Arguments.

Parses CLI arguments and dynamically resolves application version.
"""

# =============================================================================
# IMPORTS
# =============================================================================

import argparse
import os
import re
import sys
from pathlib import Path
from typing import List, Optional, Sequence

# =============================================================================
# CONSTANTS & CACHE
# =============================================================================

_VERSION_REGEX = re.compile(
    r'^\s*version\s*=\s*["\']([0-9A-Za-z_.\-+]+)["\']'
)
_CACHED_VERSION: Optional[str] = None

# =============================================================================
# HELPERS
# =============================================================================


def _get_candidate_toml_paths() -> List[Path]:
    """Assemble candidate filesystem locations for pyproject.toml."""
    candidates: List[Path] = []
    try:
        parents = Path(__file__).resolve().parents
        if len(parents) >= 3:
            candidates.append(parents[2] / "pyproject.toml")
        elif parents:
            candidates.append(parents[0] / "pyproject.toml")
    except (OSError, RuntimeError, ValueError):
        # Ignore symlink loops, permission errors, or unresolvable paths
        pass

    for env_dir in (getattr(sys, "_MEIPASS", None), os.environ.get("APPDIR")):
        if env_dir:
            candidates.append(Path(env_dir) / "pyproject.toml")

    return list(dict.fromkeys(candidates))


def _extract_version_from_file(path: Path) -> Optional[str]:
    """Extract project version from a pyproject.toml file."""
    try:
        if not path.is_file():
            return None
        section = None
        for line in path.read_text(
            encoding="utf-8-sig", errors="replace"
        ).splitlines():
            line = line.strip()
            if line.startswith("[") and line.endswith("]"):
                section = line[1:-1].strip().lower()
            elif section in (None, "project"):
                match = _VERSION_REGEX.match(line)
                if match:
                    return match.group(1)
    except (OSError, UnicodeError, ValueError):
        # Fall back to None on unreadable files, bad encodings, or IO errors
        pass
    return None


# =============================================================================
# FUNCTIONS
# =============================================================================


def get_version(*, force_refresh: bool = False) -> str:
    """Resolve application version from pyproject.toml or package metadata."""
    global _CACHED_VERSION
    if _CACHED_VERSION is not None and not force_refresh:
        return _CACHED_VERSION

    for toml_path in _get_candidate_toml_paths():
        resolved = _extract_version_from_file(toml_path)
        if resolved:
            _CACHED_VERSION = resolved
            return _CACHED_VERSION

    try:
        import importlib.metadata

        _CACHED_VERSION = importlib.metadata.version("atlas")
        return _CACHED_VERSION
    except Exception:
        # PackageNotFoundError if atlas is not installed as a package
        pass

    _CACHED_VERSION = "1.2"
    return _CACHED_VERSION


VERSION: str = get_version()


def build_parser() -> argparse.ArgumentParser:
    """Build top-level argument parser for Atlas."""
    parser = argparse.ArgumentParser(
        prog="atlas", description="Atlas Browser Backup"
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"Atlas {VERSION}",
        help="Show program's version number and exit.",
    )
    parser.add_argument(
        "--cli", action="store_true", help="Run Atlas in command-line mode."
    )
    return parser


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments safely."""
    if argv is None:
        raw = getattr(sys, "argv", None)
        argv = raw[1:] if raw is not None else []
    args, _ = build_parser().parse_known_args(argv)
    return args
