"""Atlas | UI Dialog.

Defines the main dialog UI for Atlas, including labels, progress bar,
and buttons.
"""

# =============================================================================
# IMPORTS
# =============================================================================

import logging
from typing import Tuple

from PyQt6.QtCore import QCoreApplication, QMetaObject, Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

# =============================================================================
# LOGGING
# =============================================================================

LOGGER = logging.getLogger(__name__)

# =============================================================================
# CONSTANTS
# =============================================================================

_WINDOW_FLAGS = (
    Qt.WindowType.Dialog
    | Qt.WindowType.CustomizeWindowHint
    | Qt.WindowType.WindowTitleHint
    | Qt.WindowType.WindowSystemMenuHint
    | Qt.WindowType.WindowMinimizeButtonHint
    | Qt.WindowType.WindowMaximizeButtonHint
    | Qt.WindowType.WindowCloseButtonHint
)

_LAYOUT_MARGINS: Tuple[int, int, int, int] = (20, 10, 20, 20)
_LAYOUT_SPACING: int = 6
_WINDOW_MIN_SIZE: Tuple[int, int] = (407, 290)

_CONTENT_LABELS: Tuple[Tuple[str, str], ...] = (
    ("description", "Description"),
    ("progress_description", "ProgressDescription"),
    ("completed_description", "CompletedDescription"),
    ("cancel_description", "CancelDescription"),
)

# =============================================================================
# CLASSES
# =============================================================================


class UiDialog:
    """Main dialog UI for Atlas.

    Includes backdrop, buttons, labels, and a progress bar.
    Layout-driven design that scales on resize and high-DPI displays.
    """

    def setup_ui(self, main_dialog: QDialog) -> None:
        """Initialize and arrange all UI components for the main dialog.

        Sets up the backdrop, layout, labels, progress bar, and buttons.
        The window supports resizing and maximizing; minimum size is
        enforced via ``setMinimumSize``.

        Args:
            main_dialog: The parent widget to attach all components to.

        """
        try:
            main_dialog.setObjectName("MainDialog")
            main_dialog.setMinimumSize(*_WINDOW_MIN_SIZE)
            main_dialog.setWindowFlags(_WINDOW_FLAGS)

            self._setup_backdrop(main_dialog)

            layout = QVBoxLayout(main_dialog)
            layout.setContentsMargins(*_LAYOUT_MARGINS)
            layout.setSpacing(_LAYOUT_SPACING)

            self._setup_labels(main_dialog, layout)
            self._setup_progress_bar(layout)
            self._setup_buttons(layout)

            self.retranslate_ui(main_dialog)
            QMetaObject.connectSlotsByName(main_dialog)

            LOGGER.debug("UI setup completed successfully.")
        except Exception as error:
            LOGGER.error(
                "Failed to setup UI: %s", error, exc_info=True
            )
            raise

    def _setup_backdrop(self, parent: QWidget) -> None:
        """Create the backdrop label behind all other UI elements."""
        self.backdrop = QLabel(parent)
        self.backdrop.setObjectName("Backdrop")
        self.backdrop.setGeometry(parent.rect())
        self.backdrop.lower()

    def _setup_labels(
        self, parent: QWidget, layout: QVBoxLayout
    ) -> None:
        """Set up the title, content area, and time-elapsed labels.

        Args:
            parent: The parent widget providing the base font.
            layout: The top-level layout to add all labels into.

        """
        base_font = parent.font()

        self.title = self._make_label(
            parent, base_font, scale=1.4, name="Title",
        )
        layout.addWidget(self.title)

        # Area for mutually-exclusive status labels.
        content_area = QWidget(parent)
        content_area.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        inner = QVBoxLayout(content_area)
        inner.setContentsMargins(0, 6, 0, 0)
        inner.setSpacing(0)

        for attr_name, obj_name in _CONTENT_LABELS:
            label = self._make_label(
                parent, base_font, scale=1.0, name=obj_name,
                v_policy=QSizePolicy.Policy.Expanding,
                align=(
                    Qt.AlignmentFlag.AlignTop
                    | Qt.AlignmentFlag.AlignLeft
                ),
            )
            setattr(self, attr_name, label)
            inner.addWidget(label)

        layout.addWidget(content_area, stretch=1)

        self.time_elapsed = self._make_label(
            parent, base_font, scale=0.9, name="TimeElapsed",
        )
        layout.addWidget(self.time_elapsed)
        layout.addSpacing(20)

    def _setup_progress_bar(self, layout: QVBoxLayout) -> None:
        """Set up the progress bar and add it to the layout.

        The bar occupies 65 % of the row width, with empty space on
        the right to match the original fixed-size proportions.

        Args:
            layout: The top-level layout to add the progress bar into.

        """
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setObjectName("ProgressBar")
        self.progress_bar.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)
        row.addWidget(self.progress_bar, 65)
        row.addStretch(35)
        layout.addLayout(row)

    def _setup_buttons(self, layout: QVBoxLayout) -> None:
        """Set up the OK/Cancel button box and add it to the layout.

        Args:
            layout: The top-level layout to add the button box into.

        """
        self.selection = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel,
            Qt.Orientation.Horizontal,
        )
        self.selection.setCenterButtons(False)
        self.selection.setObjectName("Selection")
        layout.addWidget(self.selection)

    @staticmethod
    def _make_label(
        parent: QWidget,
        base_font: QFont,
        scale: float,
        name: str,
        v_policy: QSizePolicy.Policy = QSizePolicy.Policy.Preferred,
        align: Qt.AlignmentFlag = (
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        ),
    ) -> QLabel:
        """Create a ``QLabel`` with scaled font, word wrap, and alignment.

        Args:
            parent: Parent widget.
            base_font: Base font to derive the scaled font from.
            scale: Multiplier applied to the base point size.
            name: Qt object name for the label.
            v_policy: Vertical size policy for the label.
            align: Text alignment flags.

        Returns:
            A fully configured ``QLabel`` instance.

        """
        font = QFont(base_font)
        font.setPointSizeF(font.pointSizeF() * scale)

        label = QLabel(parent)
        label.setFont(font)
        label.setWordWrap(True)
        label.setObjectName(name)
        label.setAlignment(align)
        label.setSizePolicy(QSizePolicy.Policy.Expanding, v_policy)
        return label

    def retranslate_ui(self, main_dialog: QDialog) -> None:
        """Apply localised text to all UI elements.

        Args:
            main_dialog: The main dialog widget whose title is also set.

        """
        tr = QCoreApplication.translate

        main_dialog.setWindowTitle(tr("MainDialog", "Atlas"))
        self.title.setText(tr(
            "MainDialog",
            '<span style="font-size:16pt;">Atlas</span> '
            '<span style="font-size:11pt; vertical-align:super;">1.0'
            "</span>",
        ))
        self.description.setText(tr(
            "MainDialog",
            "Atlas will automatically detect all installed web browsers "
            "and back up your user profiles into an output directory. "
            'Press \u201cOK\u201d to initiate the backup or '
            '\u201cCancel\u201d to exit.',
        ))
        self.progress_description.setText(tr(
            "MainDialog",
            "Backing up browser profiles. Performance may vary "
            "depending on your system\u2019s storage device.",
        ))
        self.completed_description.setText(tr(
            "MainDialog",
            "All browser profiles have been successfully backed up, "
            "compressed, and saved to the specified output folder. "
            "You may now close the application.",
        ))
        self.cancel_description.setText(tr(
            "MainDialog",
            "The backup operation was canceled. You may now safely "
            "close this window.",
        ))
        self.time_elapsed.setText(tr("MainDialog", "Time Elapsed: "))
