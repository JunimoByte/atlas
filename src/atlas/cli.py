"""Atlas | CLI Entry Point.

Provides a clean, terminal-friendly interface for running Atlas backups
without invoking the PyQt GUI. Useful for pure terminal environments
(bash, zsh, fish).
"""

# =============================================================================
# IMPORTS
# =============================================================================

import argparse
import sys

from atlas.backup.pipeline import Pipeline, PipelineResult

# =============================================================================
# FUNCTIONS
# =============================================================================


def clear_line() -> None:
    """Clear the current terminal line cross-platform."""
    if sys.stdout.isatty():
        sys.stdout.write("\r" + " " * 79 + "\r")
        sys.stdout.flush()


_LOGGED_MILESTONES: set = set()


def _on_progress(current: int, total: int) -> None:
    if total <= 0:
        return
    percent = int((current / total) * 100)
    text = f"[Backup] Progress: {percent}% ({current}/{total} files)"
    if sys.stdout.isatty():
        # Keep visible width at 78 cols to avoid wrap on 80-col terminals
        sys.stdout.write(f"\r{text[:78].ljust(78)}")
        sys.stdout.flush()
    else:
        # Only log every 10% to prevent massive log files in cron jobs
        if percent % 10 == 0 and percent not in _LOGGED_MILESTONES:
            _LOGGED_MILESTONES.add(percent)
            print(text)


def _on_scanned(msg: str) -> None:
    if sys.stdout.isatty():
        # 78 visible columns max: "[Scanning] " is 11 chars -> 67 chars for msg
        text = f"[Scanning] {msg[:67]}"
        sys.stdout.write(f"\r{text.ljust(78)}")
        sys.stdout.flush()
    # If not a TTY (cron/log file), remain completely silent during scanning
    # to prevent a 100,000-line log file output.


def _on_estimated(size: str) -> None:
    clear_line()
    print(f"Estimated Backup Size: {size}")
    if sys.stdout.isatty():
        print()


def _on_no_browsers() -> None:
    clear_line()
    print("Error: No supported browser profiles found on this system.")


def _on_disk_error(required: str, available: str) -> None:
    clear_line()
    print("Error: Insufficient disk space.")
    print(f"Required:  {required}")
    print(f"Available: {available}")


def run_cli(args: argparse.Namespace = None) -> int:
    """Execute the backup pipeline in CLI mode.

    Args:
        args: Parsed command-line arguments for future expandability.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    from atlas.lib import browsers, permissions

    # Reset per-run state so repeated calls (e.g. in tests) log correctly
    _LOGGED_MILESTONES.clear()

    if permissions.is_elevated():
        print("WARNING: Running with elevated privileges is not recommended.")

    if not browsers.verify_entries():
        print("Error: Failed to load browser configuration.")
        return 1

    print("========================================")
    print("             ATLAS CLI MODE             ")
    print("========================================")
    print("Starting backup process...\n")

    pipeline = Pipeline(
        progress_callback=_on_progress,
        scanned_callback=_on_scanned,
        estimated_callback=_on_estimated,
        no_browsers_found_callback=_on_no_browsers,
        disk_space_error_callback=_on_disk_error,
    )

    try:
        result = pipeline.run()
    except KeyboardInterrupt:
        pipeline.cancel()
        clear_line()
        print("\nBackup cancelled by user.")
        return 1
    except Exception as e:
        clear_line()
        print(f"\nAn unexpected error occurred: {e}")
        return 1

    print()  # Final newline after progress completes

    if result == PipelineResult.SUCCESS:
        print("========================================")
        print("Backup completed successfully.")
        print("========================================")
        return 0
    elif result == PipelineResult.CANCELLED:
        print("Backup was cancelled.")
        return 1
    elif result == PipelineResult.NO_BROWSERS_FOUND:
        return 1
    elif result == PipelineResult.INSUFFICIENT_DISK_SPACE:
        return 1
    else:
        print(f"Backup failed. Reason: {result.name}")
        return 1
