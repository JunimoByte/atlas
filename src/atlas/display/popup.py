"""Atlas | Display | Popup.

Flexible popup dialog system for Atlas.
Supports various message types with proper theming.
"""

# =============================================================================
# IMPORTS
# =============================================================================

import logging
import sys
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QMessageBox

from atlas.lib.themes import apply as _apply_theme

# =============================================================================
# LOGGING
# =============================================================================

LOGGER = logging.getLogger(__name__)

# =============================================================================
# CONSTANTS
# =============================================================================

ICON_MAP = {
    "INFORMATION": QMessageBox.Icon.Information,
    "WARNING": QMessageBox.Icon.Warning,
    "CRITICAL": QMessageBox.Icon.Critical,
    "QUESTION": QMessageBox.Icon.Question,
}

BUTTON_MAP = {
    "ACKNOWLEDGE": QMessageBox.StandardButton.Ok,
    "CONFIRM_DECLINE": QMessageBox.StandardButton.Yes
    | QMessageBox.StandardButton.No,
    "ACKNOWLEDGE_CANCEL": QMessageBox.StandardButton.Ok
    | QMessageBox.StandardButton.Cancel,
    "CONFIRM_DECLINE_CANCEL": (
        QMessageBox.StandardButton.Yes
        | QMessageBox.StandardButton.No
        | QMessageBox.StandardButton.Cancel
    ),
}

DEFAULT_BUTTON = {
    "ACKNOWLEDGE": QMessageBox.StandardButton.Ok,
    "CONFIRM_DECLINE": QMessageBox.StandardButton.Yes,
    "ACKNOWLEDGE_CANCEL": QMessageBox.StandardButton.Ok,
    "CONFIRM_DECLINE_CANCEL": QMessageBox.StandardButton.Yes,
}

DEFAULT_STAY_ON_TOP = True

# =============================================================================
# FUNCTIONS
# =============================================================================


def show(
    title: str,
    text: str,
    icon: str = "INFORMATION",
    buttons: str = "ACKNOWLEDGE",
    informative_text: Optional[str] = None,
    detailed_text: Optional[str] = None,
    stay_on_top: bool = DEFAULT_STAY_ON_TOP,
) -> int:
    """Show a flexible popup dialog with theming support.

    Args:
        title: Window title.
        text: Main message text.
        icon: Icon type (INFORMATION, WARNING, CRITICAL, QUESTION).
        buttons: Button group type.
        informative_text: Optional informative text.
        detailed_text: Optional detailed text.
        stay_on_top: Whether the window stays on top.

    Returns:
        Result of the message box execution.
    """
    try:
        app = QApplication.instance() or QApplication(sys.argv)
        app.setQuitOnLastWindowClosed(True)

        msg = QMessageBox()
        msg.setObjectName("PopupMessageBox")
        msg.setWindowTitle(title)
        msg.setText(text)
        msg.setIcon(ICON_MAP.get(icon, QMessageBox.Icon.Information))
        msg.setStandardButtons(
            BUTTON_MAP.get(buttons, QMessageBox.StandardButton.Ok)
        )
        msg.setDefaultButton(
            DEFAULT_BUTTON.get(buttons, QMessageBox.StandardButton.Ok)
        )

        if informative_text:
            msg.setInformativeText(informative_text)
        if detailed_text:
            msg.setDetailedText(detailed_text)

        flags = (
            Qt.WindowType.Dialog | Qt.WindowType.MSWindowsFixedSizeDialogHint
        )
        if stay_on_top:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        msg.setWindowFlags(flags)

        for button in msg.buttons():
            button.setIcon(QIcon())

        try:
            _apply_theme(msg)
        except Exception as error:
            LOGGER.debug("Theme application failed: %s", error)

        return msg.exec()
    except Exception as error:
        LOGGER.error("Failed to show popup: %s", error, exc_info=True)
        return int(QMessageBox.StandardButton.Ok)


# =============================================================================
# WRAPPERS
# =============================================================================


def show_warning(
    title: str, message: str, details: Optional[str] = None
) -> None:
    """Show a warning popup.

    Args:
        title: Window title.
        message: Warning message.
        details: Additional details.

    """
    show(
        title,
        "<b>{}</b>".format(message),
        icon="WARNING",
        buttons="ACKNOWLEDGE",
        informative_text=details,
        stay_on_top=True,
    )


def show_error(
    title: str, message: str, details: Optional[str] = None
) -> None:
    """Show a critical error popup.

    Args:
        title: Window title.
        message: Error message.
        details: Additional details.

    """
    show(
        title,
        "<b>{}</b>".format(message),
        icon="CRITICAL",
        buttons="ACKNOWLEDGE",
        informative_text=details,
        stay_on_top=True,
    )


def show_info(
    title: str, message: str, details: Optional[str] = None
) -> int:
    """Show an informational popup.

    Args:
        title: Window title.
        message: Informational message.
        details: Additional details.

    Returns:
        Result of the message box execution.

    """
    return show(
        title,
        "<b>{}</b>".format(message),
        icon="INFORMATION",
        buttons="ACKNOWLEDGE",
        informative_text=details,
        stay_on_top=False,
    )


def show_question(
    title: str,
    message: str,
    details: Optional[str] = None,
    cancel_button: bool = False,
) -> bool:
    """Show a question popup with Yes/No (and optional Cancel) buttons.

    Args:
        title: Window title.
        message: Question text.
        details: Additional details.
        cancel_button: Whether to include Cancel button.

    Returns:
        True if user clicked Yes, False otherwise.

    """
    buttons = "CONFIRM_DECLINE_CANCEL" if cancel_button else "CONFIRM_DECLINE"
    return show(
        title,
        "<b>{}</b>".format(message),
        icon="QUESTION",
        buttons=buttons,
        informative_text=details,
        stay_on_top=False,
    ) == QMessageBox.StandardButton.Yes
