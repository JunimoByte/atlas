"""Atlas | Display | Signals.

Defines application-wide events and acts as a contract between
the Controller and the Window. All signal payloads are documented
with expected types for clarity and IDE support.
"""

# =============================================================================
# IMPORTS
# =============================================================================

from PyQt6.QtCore import QObject, pyqtSignal

# =============================================================================
# CLASSES
# =============================================================================


class Signals(QObject):
    """Define all application signals for Atlas.

    Signals act as a contract between the Controller (logic)
    and the Window (UI). They contain no logic or state.
    """

    # Backup workflow lifecycle
    backup_started = pyqtSignal()
    """Emit when a backup process starts. No arguments."""

    backup_finished = pyqtSignal()
    """Emit when a backup process completes successfully. No arguments."""

    backup_cancelled = pyqtSignal()
    """Emit when a backup process is cancelled by the user. No arguments."""

    # Progress reporting
    progress = pyqtSignal(int, int)
    """Report backup progress.

    Args:
        current: Current progress count
        total: Total items to process
    """

    estimated_size = pyqtSignal(str)
    """Report estimated backup size.

    Args:
        size_str: Formatted size string (e.g., '120 MB')
    """

    scanned_entries = pyqtSignal(str)
    """Report latest scanned entry.

    Args:
        entry_name: Name or description of the scanned entry
    """

    # Elapsed time
    elapsed_time = pyqtSignal(int)
    """Report elapsed backup time.

    Args:
        seconds: Total seconds elapsed since backup start
    """

    # Error reporting
    disk_space_error = pyqtSignal(str, str)
    """Report insufficient disk space.

    Args:
        required: Space required for backup
        available: Space currently available
    """

    no_browsers_found = pyqtSignal()
    """Emit when no supported browsers are detected. No arguments."""

    worker_error = pyqtSignal(str)
    """Emit when the worker thread encounters an unhandled exception or crash.

    Args:
        message: Error message to display to the user.
    """
