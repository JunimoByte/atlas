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

from atlas.compatibility.qt import QtCore, QtGui, QtWidgets
from atlas.lib.themes import apply as _apply_theme

# =============================================================================
# LOGGING
# =============================================================================

LOGGER = logging.getLogger(__name__)

# =============================================================================
# CONSTANTS
# =============================================================================

ICON_MAP = {
    "INFORMATION": QtWidgets.QMessageBox.Icon.Information,
    "WARNING": QtWidgets.QMessageBox.Icon.Warning,
    "CRITICAL": QtWidgets.QMessageBox.Icon.Critical,
    "QUESTION": QtWidgets.QMessageBox.Icon.Question,
}

BUTTON_MAP = {
    "ACKNOWLEDGE": QtWidgets.QMessageBox.StandardButton.Ok,
    "CONFIRM_DECLINE": QtWidgets.QMessageBox.StandardButton.Yes
    | QtWidgets.QMessageBox.StandardButton.No,
    "ACKNOWLEDGE_CANCEL": QtWidgets.QMessageBox.StandardButton.Ok
    | QtWidgets.QMessageBox.StandardButton.Cancel,
    "CONFIRM_DECLINE_CANCEL": (
        QtWidgets.QMessageBox.StandardButton.Yes
        | QtWidgets.QMessageBox.StandardButton.No
        | QtWidgets.QMessageBox.StandardButton.Cancel
    ),
}

DEFAULT_BUTTON = {
    "ACKNOWLEDGE": QtWidgets.QMessageBox.StandardButton.Ok,
    "CONFIRM_DECLINE": QtWidgets.QMessageBox.StandardButton.Yes,
    "ACKNOWLEDGE_CANCEL": QtWidgets.QMessageBox.StandardButton.Ok,
    "CONFIRM_DECLINE_CANCEL": QtWidgets.QMessageBox.StandardButton.Yes,
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
        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(
            sys.argv
        )
        app.setQuitOnLastWindowClosed(True)

        msg = QtWidgets.QMessageBox()
        msg.setObjectName("PopupMessageBox")
        msg.setWindowTitle(title)
        msg.setText(text)
        msg.setIcon(ICON_MAP.get(icon, QtWidgets.QMessageBox.Icon.Information))
        msg.setStandardButtons(
            BUTTON_MAP.get(buttons, QtWidgets.QMessageBox.StandardButton.Ok)
        )
        msg.setDefaultButton(
            DEFAULT_BUTTON.get(
                buttons, QtWidgets.QMessageBox.StandardButton.Ok
            )
        )

        if informative_text:
            msg.setInformativeText(informative_text)
        if detailed_text:
            msg.setDetailedText(detailed_text)

        flags = (
            QtCore.Qt.WindowType.Dialog
            | QtCore.Qt.WindowType.MSWindowsFixedSizeDialogHint
        )
        if stay_on_top:
            flags |= QtCore.Qt.WindowType.WindowStaysOnTopHint
        msg.setWindowFlags(flags)

        for button in msg.buttons():
            button.setIcon(QtGui.QIcon())

        try:
            _apply_theme(msg)
        except Exception as error:
            LOGGER.debug("Theme application failed: %s", error)

        return msg.exec()
    except Exception as error:
        LOGGER.error("Failed to show popup: %s", error, exc_info=True)
        return int(QtWidgets.QMessageBox.StandardButton.Ok)


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


def show_info(title: str, message: str, details: Optional[str] = None) -> int:
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
    return (
        show(
            title,
            "<b>{}</b>".format(message),
            icon="QUESTION",
            buttons=buttons,
            informative_text=details,
            stay_on_top=False,
        )
        == QtWidgets.QMessageBox.StandardButton.Yes
    )
