"""Atlas | Display | Controls.

UI helpers and formatting functions for Window class.
Handles button manipulation, visibility, and elapsed time formatting.
"""

# =============================================================================
# IMPORTS
# =============================================================================

import logging
from typing import Any, Callable, Mapping, Optional, Tuple

from PyQt6.QtWidgets import QAbstractButton, QDialogButtonBox

# =============================================================================
# LOGGING
# =============================================================================

LOGGER = logging.getLogger(__name__)

# =============================================================================
# CONSTANTS
# =============================================================================

VALID_SIGNALS: Tuple[str, ...] = ("accepted", "rejected")
SECONDS_PER_HOUR: int = 3600
SECONDS_PER_MINUTE: int = 60

# =============================================================================
# ELEMENTS
# =============================================================================


def set_text(button_box: QDialogButtonBox, name: str, text: str) -> None:
    """Set the text of a standard button safely.

    Args:
        button_box: The button box containing the button.
        name: The name of the StandardButton (e.g., 'Ok', 'Cancel').
        text: The new text to display.
    """
    button = _get_button(button_box, name)
    if button:
        button.setText(text)


def set_button_visible(
    button_box: QDialogButtonBox, name: str, visible: bool
) -> None:
    """Set the visibility of a standard button safely.

    Args:
        button_box: The button box.
        name: The name of the StandardButton (e.g., 'Ok', 'Cancel').
        visible: Whether the button should be visible.
    """
    button = _get_button(button_box, name)
    if button:
        button.setVisible(visible)


def set_connection(
    button_box: QDialogButtonBox, name: str, command: Callable
) -> None:
    """Connect a standard button signal to a command safely.

    Disconnect any existing connections before adding the new one.

    Args:
        button_box: The button box.
        name: The signal name ('accepted' or 'rejected').
        command: The slot to connect to.
    """
    if name not in VALID_SIGNALS or not callable(command):
        return

    signal = getattr(button_box, name, None)
    if signal:
        try:
            signal.disconnect()
        except (TypeError, RuntimeError):
            pass
        signal.connect(command)


def configure_button(
    button_box: QDialogButtonBox, name: str, conf: Mapping[str, Any]
) -> None:
    """Configure button visibility and text using a dictionary.

    Args:
        button_box: The button box.
        name: The name of the button.
        conf: Config dict with keys 'visible' and 'text'.
    """
    set_button_visible(button_box, name, conf.get("visible", False))
    if "text" in conf:
        set_text(button_box, name, conf["text"])


def _get_button(
    button_box: QDialogButtonBox, name: str
) -> Optional[QAbstractButton]:
    """Retrieve a button safely by name."""
    try:
        type_ = QDialogButtonBox.StandardButton[name]  # type: ignore
        return button_box.button(type_)
    except (KeyError, AttributeError):
        return None


# =============================================================================
# FORMATTING
# =============================================================================


def format_elapsed_time(elapsed: int, info: str = "") -> str:
    """Format seconds into a human-readable string with optional context info.

    Args:
        elapsed: Total seconds elapsed (should be non-negative).
        info: Additional context string (e.g., scanned item).

    Returns:
        Formatted string like 'Time Elapsed: 1m 30s (Scanning...)'.
    """
    hours, rem = divmod(elapsed, SECONDS_PER_HOUR)
    minutes, seconds = divmod(rem, SECONDS_PER_MINUTE)

    parts = []
    if hours:
        parts.append("{}h".format(hours))
    if minutes or hours:
        parts.append("{}m".format(minutes))
    parts.append("{}s".format(seconds))

    base = "Time Elapsed: {}".format(' '.join(parts))
    return "{} ({})".format(base, info) if info else base
