"""Atlas | Display | Window.

Main application window for backup operations.
Handles UI initialization, worker thread management, progress tracking,
and user interactions.
"""

# =============================================================================
# IMPORTS
# =============================================================================

import logging
from enum import Enum
from typing import Any, Dict, Optional, Tuple

from PyQt6.QtCore import QCoreApplication, QSize
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QDialog

from atlas.display.controller import Controller
from atlas.display.controls import (
    _get_button,
    configure_button,
    format_elapsed_time,
    set_connection,
)
from atlas.display.signals import Signals
from atlas.lib.integration import open_folder
from atlas.ui.interface import UiDialog

# =============================================================================
# LOGGING
# =============================================================================

LOGGER = logging.getLogger(__name__)

# =============================================================================
# CONSTANTS
# =============================================================================

VALID_SIGNALS: Tuple[str, ...] = (
    "accepted",
    "rejected",
)
BUTTON_NAMES: Tuple[str, ...] = ("Ok", "Cancel")
UI_ELEMENTS: Tuple[str, ...] = (
    "progress_bar",
    "progress_description",
    "completed_description",
    "cancel_description",
    "time_elapsed",
    "description",
)

# =============================================================================
# CLASSES
# =============================================================================


class UIMode(Enum):
    """UI display mode configuration."""

    IDLE = "idle"
    SCANNING = "scanning"
    COMPLETED = "completed"
    ERROR = "error"


class Window(QDialog):
    """Main application window for backup operations.

    Handle UI initialization, worker thread management, button controls,
    progress tracking, elapsed time display, and error handling.
    """

    UI_MODE_CONFIG = {
        UIMode.IDLE: (
            ("description",),
            {"visible": True, "text": "OK", "command": "scan"},
            {"visible": True, "text": "Cancel", "command": "close"},
        ),
        UIMode.SCANNING: (
            ("progress_bar", "progress_description", "time_elapsed"),
            {"visible": False},
            {
                "visible": True,
                "text": "Cancel",
                "command": "_handle_cancel_button",
            },
        ),
        UIMode.COMPLETED: (
            ("completed_description",),
            {"visible": True, "text": "View", "command": "open_output_folder"},
            {"visible": True, "text": "Close", "command": "close"},
        ),
        UIMode.ERROR: (
            ("cancel_description",),
            {"visible": False},
            {"visible": True, "text": "Close", "command": "close"},
        ),
    }

    def __init__(self) -> None:
        """Initialize the main window and prepare UI."""
        super().__init__()
        self.formatted_size: str = ""
        self._last_elapsed_text: str = ""
        self.latest_scanned_info: str = ""

        self.signals = Signals()
        self.controller = Controller(self.signals)
        self._connect_signals()

        try:
            self._setup_ui()
            self._validate_ui_dependencies()
            self._setup_buttons()
            self._prepare_home()
            LOGGER.info("Window initialized successfully")
        except Exception as error:
            LOGGER.error(
                "Failed to initialize window: %s", error, exc_info=True
            )
            raise

    # =========================================================================
    # INITIALIZATION & SIGNALS
    # =========================================================================

    def _connect_signals(self) -> None:
        """Connect global signals to UI slots using mappings."""
        signal_map = {
            "backup_started":  self._on_backup_started,
            "backup_finished": self.complete,
            "backup_cancelled": self.reject,
            "progress":        self._update_progress,
            "elapsed_time":    self._update_elapsed_time,
            "estimated_size":  self._set_formatted_size,
            "scanned_entries": self._set_scanned_info,
            "disk_space_error": self._handle_disk_space_error,
            "no_browsers_found": self._handle_no_browsers,
            "worker_error":    self._handle_worker_error,
        }
        for signal_name, slot in signal_map.items():
            getattr(self.signals, signal_name).connect(slot)

    def _setup_ui(self) -> None:
        """Initialize the interface and set up the window."""
        self.interface = UiDialog()
        self.interface.setup_ui(self)
        LOGGER.debug("UI setup completed")

    def _validate_ui_dependencies(self) -> None:
        """Assert all UI elements and method commands exist at startup."""
        for name in UI_ELEMENTS:
            if not hasattr(self.interface, name):
                raise AttributeError(f"UI element '{name}' not found on interface")
                
        for mode, config in self.UI_MODE_CONFIG.items():
            _, *btn_confs = config
            for conf in btn_confs:
                cmd = conf.get("command")
                if isinstance(cmd, str) and not hasattr(self, cmd):
                    raise AttributeError(
                        f"UI_MODE_CONFIG references missing method '{cmd}' in mode {mode.name}"
                    )

    def _setup_buttons(self) -> None:
        """Remove icons from buttons for Linux compatibility."""
        for name in BUTTON_NAMES:
            button = _get_button(self.interface.selection, name)
            if button:
                button.setIcon(QIcon())
                button.setIconSize(QSize(0, 0))

    def _prepare_home(self) -> None:
        """Prepare the home state of the UI."""
        self._set_ui_mode(UIMode.IDLE)
        # Ensure buttons are re-enabled in case of a previous cancel
        cancel_btn = _get_button(self.interface.selection, "Cancel")
        if cancel_btn:
            cancel_btn.setEnabled(True)
        LOGGER.debug("Home state prepared")

    # =========================================================================
    # UI MODE MANAGEMENT
    # =========================================================================

    def _set_ui_mode(
        self, mode: UIMode, error_text: Optional[str] = None
    ) -> None:
        """Set the UI elements visibility based on the active mode."""
        ui = self.interface

        # Default all specialized elements to hidden
        for name in UI_ELEMENTS:
            getattr(ui, name).setVisible(False)

        # Mode configuration: (Visible Elements, Button Configs...)
        # Each button config corresponds to a button in BUTTON_NAMES
        config: Tuple = self.UI_MODE_CONFIG.get(
            mode, ([],) + ({},) * len(BUTTON_NAMES)
        )
        visible_elements, *button_confs = config

        # Apply visibility for UI elements
        for name in visible_elements:
            getattr(ui, name).setVisible(True)

        self._apply_mode_specific_logic(mode, error_text)

        # Configure all buttons dynamically
        for btn_name, signal_name, conf in zip(
            BUTTON_NAMES, VALID_SIGNALS, button_confs
        ):
            self._apply_button_config(btn_name, signal_name, conf)

        ui.selection.setVisible(True)
        LOGGER.debug("UI mode set to: %s", mode.value)

    def _apply_mode_specific_logic(
        self, mode: UIMode, error_text: Optional[str]
    ) -> None:
        """Handle state mutation specific to certain UI modes."""
        if mode == UIMode.SCANNING:
            self.interface.progress_bar.setValue(0)
        elif mode == UIMode.ERROR and error_text:
            self.interface.cancel_description.setText(error_text)

    def _apply_button_config(
        self, btn: str, signal: str, conf: Dict[str, Any]
    ) -> None:
        """Apply config and connect signals for a button."""
        configure_button(self.interface.selection, btn, conf)

        if "command" in conf:
            cmd = conf["command"]
            if isinstance(cmd, str):
                cmd_name = cmd
                cmd = getattr(self, cmd_name, None)
                if not cmd:
                    LOGGER.warning(
                        "Could not resolve command method: '%s'", cmd_name
                    )

            if cmd:
                set_connection(self.interface.selection, signal, cmd)

    # =========================================================================
    # PROGRESS & TIME
    # =========================================================================

    def _update_progress(self, current: int, total: int) -> None:
        """Update the progress bar as percentage."""
        if total <= 0:
            return
        percentage = min(100, max(0, int((current / total) * 100)))
        self.interface.progress_bar.setValue(percentage)

    def _update_elapsed_time(self, elapsed: int) -> None:
        """Update elapsed time display only if changed."""
        info = self.formatted_size or self.latest_scanned_info
        text = format_elapsed_time(elapsed, info)
        if text != self._last_elapsed_text:
            self.interface.time_elapsed.setText(text)
            self._last_elapsed_text = text

    # =========================================================================
    # OPERATIONS
    # =========================================================================

    def scan(self) -> None:
        """Initiate the backup scan process.

        Delegate to the controller to start the worker thread.
        """
        self.controller.start_backup()

    def _on_backup_started(self) -> None:
        """Handle backup started event."""
        self.formatted_size = ""
        self.latest_scanned_info = ""
        self._last_elapsed_text = ""
        self._set_ui_mode(UIMode.SCANNING)
        LOGGER.info("Backup Scan Initiated")

    def _set_formatted_size(self, value: str) -> None:
        """Store the latest formatted size estimate."""
        self.formatted_size = value

    def _set_scanned_info(self, value: str) -> None:
        """Store the latest scanned entry description."""
        self.latest_scanned_info = value

    def complete(self) -> None:
        """Handle successful backup completion.

        Update the UI to the COMPLETED state and log the success.
        """
        self._set_ui_mode(UIMode.COMPLETED)
        LOGGER.info("Backup completed successfully")

    def open_output_folder(self) -> None:
        """Open the backup output folder."""
        open_folder()

    def _handle_disk_space_error(self, required: str, available: str) -> None:
        """Handle disk space error."""
        msg = (
            "Backup failed due to insufficient disk space. "
            "Please free up storage on your drive and try again."
        )
        self._set_ui_mode(UIMode.ERROR, msg)
        LOGGER.error(
            "Disk space error: %s available, %s required", available, required
        )

    def _handle_no_browsers(self) -> None:
        """Handle case where no browsers were found."""
        msg = (
            "No supported browsers were found on this system.\n\n"
            "There was nothing to back up."
        )
        self._set_ui_mode(UIMode.ERROR, msg)
        LOGGER.info("UI updated: no browsers found")

    def _handle_worker_error(self, message: str) -> None:
        """Handle unexpected worker errors or crashes.

        Args:
            message: Error message to display.
        """
        self._set_ui_mode(UIMode.ERROR, message)
        LOGGER.error("Worker error displayed: %s", message)

    def _handle_cancel_button(self) -> None:
        """Handle cancel button press."""
        LOGGER.info("Cancel button pressed")
        self.interface.time_elapsed.setText("Stopping scan...")

        # Disable the cancel button so it cannot be spammed
        cancel_btn = _get_button(self.interface.selection, "Cancel")
        if cancel_btn:
            cancel_btn.setEnabled(False)

        # Allow the UI to update with "Stopping scan..." before shutting down.
        # This is safe here because cancel_backup() does not re-enter the event loop.
        QCoreApplication.processEvents()

        self.controller.cancel_backup()

    # =========================================================================
    # DIALOGUE & EVENTS
    # =========================================================================

    def closeEvent(self, event: Any) -> None:
        """Handle cleanup on close."""
        LOGGER.debug("Window closing")
        self.controller.cleanup()
        LOGGER.debug("Event accepted")
        event.accept()

    def resizeEvent(self, event: Any) -> None:
        """Handle scaling of the backdrop on window resize."""
        super().resizeEvent(event)

        if hasattr(self, "interface") and hasattr(self.interface, "backdrop"):
            self.interface.backdrop.setGeometry(self.rect())
