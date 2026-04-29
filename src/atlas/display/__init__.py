"""Atlas | Display.

User interface package for Atlas.

Provides popup dialogs, widget helpers, and signal definitions.
Application-layer classes such as Controller and Window are consumed
directly by their callers and are not re-exported here.
"""

from .controls import (
    configure_button,
    format_elapsed_time,
    set_button_visible,
    set_connection,
    set_text,
)
from .popup import show_warning
from .signals import Signals

__all__ = [
    "Signals",
    "show_warning",
    "set_text",
    "set_button_visible",
    "set_connection",
    "configure_button",
    "format_elapsed_time",
]
