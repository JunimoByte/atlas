"""Atlas | Packages.

Utility packages for browser detection, configuration
loading, and theming.

Note: ``integration`` and ``permissions`` are purposely not
re-exported here.  Both modules import from ``atlas.display``,
so including them would create a circular import with
``atlas.display.popup``, which imports ``atlas.lib.themes``
and therefore triggers this ``__init__``.
"""

from .browsers import grab, verify_entries
from .read import load_json
from .themes import apply, backdrop, icon, initialize

__all__ = [
    "verify_entries",
    "grab",
    "load_json",
    "initialize",
    "apply",
    "backdrop",
    "icon",
]
