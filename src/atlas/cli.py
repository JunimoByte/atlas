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
from typing import Optional

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


def _apply_output_directory(args: Optional[argparse.Namespace]) -> bool:
    """Apply custom output directory from CLI arguments if specified.

    Returns:
        bool: True if valid or omitted, False on invalid directory.
    """
    if not (args and getattr(args, "output", None)):
        return True

    from atlas.backup import archive

    try:
        out_dir = archive.set_zip_output_dir(args.output)
        print(f"Output Directory: {out_dir}")
        return True
    except Exception as err:
        print(f"Error: Invalid output directory '{args.output}': {err}")
        return False


def run_list(args: Optional[argparse.Namespace] = None) -> int:
    """List detected browser profiles without performing a backup.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code (0 for success, 1 on error).
    """
    from atlas.backup import size
    from atlas.lib import browsers, permissions

    if permissions.is_elevated():
        print("WARNING: Running with elevated privileges is not recommended.")

    if not browsers.verify_entries():
        print("Error: Failed to load browser configuration.")
        return 1

    pipeline = Pipeline()
    try:
        matches = pipeline.scan_profiles()
    except KeyboardInterrupt:
        print("\nScan cancelled by user.")
        return 1

    if not matches:
        print("No supported browser profiles found on this system.")
        return 0

    print("========================================")
    print("       DETECTED BROWSER PROFILES        ")
    print("========================================")

    total_profiles = 0
    for browser in sorted(matches.keys()):
        paths = matches[browser]
        if not paths:
            continue
        print(f"[{browser}]")
        for path in sorted(paths):
            total_profiles += 1
            print(f"  - {path}")
        print()

    try:
        total_bytes = pipeline.estimate_size(matches)
        formatted_size = size.format_size(total_bytes)
    except KeyboardInterrupt:
        print("\nSize estimation cancelled by user.")
        return 1

    print("----------------------------------------")
    print(f"Total Profiles: {total_profiles}")
    print(f"Estimated Size: {formatted_size}")
    print("========================================")
    return 0


def _handle_pipeline_result(result: PipelineResult) -> int:
    """Format and return exit code for pipeline execution outcome."""
    if result == PipelineResult.SUCCESS:
        print("========================================")
        print("Backup completed successfully.")
        print("========================================")
        return 0
    if result == PipelineResult.CANCELLED:
        print("Backup was cancelled.")
        return 1
    if result in (
        PipelineResult.NO_BROWSERS_FOUND,
        PipelineResult.INSUFFICIENT_DISK_SPACE,
    ):
        return 1
    print(f"Backup failed. Reason: {result.name}")
    return 1


def run_cli(args: Optional[argparse.Namespace] = None) -> int:
    """Execute the backup pipeline in CLI mode.

    Args:
        args: Parsed command-line arguments for future expandability.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    if args and getattr(args, "list", False):
        return run_list(args)

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

    if not _apply_output_directory(args):
        return 1

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

    return _handle_pipeline_result(result)
