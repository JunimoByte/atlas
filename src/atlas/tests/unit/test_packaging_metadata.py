"""Atlas | Tests | Packaging Metadata.

Guard PEP 508 markers against host kernel versions that are not PEP 440.
"""

# =============================================================================
# IMPORTS
# =============================================================================

import re
from pathlib import Path
from typing import Dict, List

from packaging.markers import default_environment
from packaging.requirements import Requirement

# =============================================================================
# CONSTANTS
# =============================================================================

PYPROJECT_PATH = Path(__file__).resolve().parents[4] / "pyproject.toml"


# =============================================================================
# HELPERS
# =============================================================================


def _runtime_requirements() -> List[Requirement]:
    """Read the simple runtime dependency list without a TOML dependency."""
    requirements: List[Requirement] = []
    in_dependencies = False

    for line in PYPROJECT_PATH.read_text(encoding="utf-8").splitlines():
        if line.strip() == "dependencies = [":
            in_dependencies = True
            continue
        if in_dependencies and line.strip() == "]":
            break
        if not in_dependencies:
            continue

        match = re.match(r'^\s*"(?P<requirement>[^"]+)",\s*$', line)
        if match:
            requirements.append(Requirement(match.group("requirement")))

    return requirements


def _environment(
    platform_system: str, python_version: str
) -> Dict[str, str]:
    """Build a marker environment with a common non-PEP-440 kernel string."""
    environment = default_environment()
    environment.update(
        {
            "platform_system": platform_system,
            "platform_release": "6.17.0-1022-azure",
            "python_version": python_version,
            "python_full_version": f"{python_version}.0",
            "sys_platform": platform_system.lower(),
        }
    )
    return environment


# =============================================================================
# TESTS
# =============================================================================


def test_runtime_markers_handle_non_pep440_kernel_releases() -> None:
    """Dependency selection cannot parse Linux kernel strings as versions."""
    requirements = _runtime_requirements()

    linux_py38 = {
        requirement.name
        for requirement in requirements
        if requirement.marker
        and requirement.marker.evaluate(_environment("Linux", "3.8"))
    }
    linux_py39 = {
        requirement.name
        for requirement in requirements
        if requirement.marker
        and requirement.marker.evaluate(_environment("Linux", "3.9"))
    }

    assert linux_py38 == {"PyQt5"}
    assert linux_py39 == {"PyQt6"}


def test_bsd_and_solaris_have_no_pypi_qt_runtime_requirement() -> None:
    """BSD and Solaris use native Qt packages instead of PyPI wheels."""
    requirements = _runtime_requirements()

    for platform_system in ("FreeBSD", "SunOS"):
        active = {
            requirement.name
            for requirement in requirements
            if requirement.marker
            and requirement.marker.evaluate(
                _environment(platform_system, "3.9")
            )
        }
        assert active == set()
