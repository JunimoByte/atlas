"""Atlas | Tests | Architecture Contracts.

Minimal architectural guard test ensuring that application code strictly
honours the dual-binding Qt compatibility contract.
"""

# =============================================================================
# IMPORTS
# =============================================================================

import ast
from pathlib import Path
from typing import List, Tuple

from atlas.compatibility import qt

# =============================================================================
# CONSTANTS
# =============================================================================

_FORBIDDEN_PACKAGES = ("PyQt5", "PyQt6", "PySide2", "PySide6")

# =============================================================================
# TESTS
# =============================================================================


def test_no_direct_pyqt_imports() -> None:
    """Ensure no application modules import directly from PyQt or PySide.

    All modules must import Qt classes through atlas.compatibility.qt to
    preserve dual-binding runtime compatibility and headless testing.
    """
    repo_root = Path(__file__).resolve().parents[4]
    src_atlas = repo_root / "src" / "atlas"
    allowed_compatibility_module = (
        src_atlas / "compatibility" / "qt.py"
    ).resolve()

    violations: List[Tuple[str, int, str]] = []

    for py_file in src_atlas.rglob("*.py"):
        resolved_path = py_file.resolve()
        # Skip the compatibility module itself and the unit tests directory
        if (
            resolved_path == allowed_compatibility_module
            or "tests" in py_file.parts
        ):
            continue

        source_code = py_file.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source_code, filename=str(py_file))

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if any(
                        alias.name.startswith(pkg)
                        for pkg in _FORBIDDEN_PACKAGES
                    ):
                        violations.append(
                            (py_file.name, node.lineno, alias.name)
                        )
            elif isinstance(node, ast.ImportFrom):
                if node.module and any(
                    node.module.startswith(pkg) for pkg in _FORBIDDEN_PACKAGES
                ):
                    violations.append((py_file.name, node.lineno, node.module))

    assert not violations, (
        "Direct Qt imports detected outside atlas.compatibility.qt. "
        f"Violations: {violations}"
    )


def test_qt_compatibility_layer_exports() -> None:
    """Ensure atlas.compatibility.qt exposes required Qt namespaces."""
    assert hasattr(qt, "QtCore"), "qt compatibility missing QtCore"
    assert hasattr(qt, "QtGui"), "qt compatibility missing QtGui"
    assert hasattr(qt, "QtWidgets"), "qt compatibility missing QtWidgets"
    assert getattr(qt, "QT_API") in ("PyQt6", "PyQt5"), "Invalid QT_API value"
