"""Atlas | Compatibility | Qt.

Unified Qt API layer. Detects and binds to the available
Qt implementation (PyQt6 or PyQt5) at import time.

All Atlas modules must import Qt classes through this
module rather than importing directly from PyQt.

Usage::

    from atlas.compatibility.qt import QtCore
    from atlas.compatibility.qt import QtGui
    from atlas.compatibility.qt import QtWidgets
"""

# =============================================================================
# IMPORTS
# =============================================================================

import logging

# =============================================================================
# LOGGING
# =============================================================================

LOGGER = logging.getLogger(__name__)

# =============================================================================
# QT BINDING RESOLUTION
# =============================================================================

QT_API = None
"""Name of the active Qt binding ('PyQt6' or 'PyQt5')."""

try:
    from PyQt6 import QtCore, QtGui, QtWidgets
    QT_API = "PyQt6"
except ImportError:
    try:
        from PyQt5 import QtCore, QtGui, QtWidgets  # noqa: F401
        QT_API = "PyQt5"
    except ImportError:
        raise ImportError(
            "Atlas requires PyQt6 or PyQt5. "
            "Neither package was found."
        )

LOGGER.debug("Qt binding resolved: %s", QT_API)
