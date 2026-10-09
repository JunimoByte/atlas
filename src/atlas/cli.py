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
from typing import Dict, List, Optional

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


def _is_quiet(args: Optional[argparse.Namespace]) -> bool:
    """Return True if quiet execution was requested."""
    return bool(args and getattr(args, "quiet", False))


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


def _on_no_browsers(
    target: Optional[str] = None, quiet: bool = False
) -> None:
    clear_line()
    out = sys.stderr if quiet else sys.stdout
    if target:
        print(
            f"Error: No profiles found on this system for '{target}'.",
            file=out,
        )
    else:
        print(
            "Error: No supported browser profiles found on this system.",
            file=out,
        )


def _on_disk_error(
    required: str, available: str, quiet: bool = False
) -> None:
    clear_line()
    out = sys.stderr if quiet else sys.stdout
    print("Error: Insufficient disk space.", file=out)
    print(f"Required:  {required}", file=out)
    print(f"Available: {available}", file=out)


def _apply_output_directory(
    args: Optional[argparse.Namespace], quiet: bool = False
) -> bool:
    """Apply custom output directory from CLI arguments if specified.

    Returns:
        bool: True if valid or omitted, False on invalid directory.
    """
    if not (args and getattr(args, "output", None)):
        return True

    from atlas.backup import archive

    try:
        out_dir = archive.set_zip_output_dir(args.output)
        if not quiet:
            print(f"Output Directory: {out_dir}")
        return True
    except Exception as err:
        out = sys.stderr if quiet else sys.stdout
        print(
            f"Error: Invalid output directory '{args.output}': {err}",
            file=out,
        )
        return False


def _verify_environment(quiet: bool = False) -> bool:
    """Validate system configuration and issue privilege warnings.

    Returns:
        bool: True if configuration is valid, False otherwise.
    """
    from atlas.lib import browsers, permissions

    if permissions.is_elevated() and not quiet:
        print("WARNING: Running with elevated privileges is not recommended.")

    if not browsers.verify_entries():
        out = sys.stderr if quiet else sys.stdout
        print("Error: Failed to load browser configuration.", file=out)
        return False

    return True


def _print_banner(title: str, quiet: bool = False) -> None:
    """Print a standardized ASCII header banner."""
    if quiet:
        return
    separator = "=" * 40
    print(separator)
    print(title.center(40).rstrip())
    print(separator)


def _handle_pipeline_result(
    result: PipelineResult, quiet: bool = False
) -> int:
    """Format and return exit code for pipeline execution outcome."""
    out = sys.stderr if quiet else sys.stdout
    if result == PipelineResult.SUCCESS:
        if not quiet:
            print("=" * 40)
            print("Backup completed successfully.")
            print("=" * 40)
        return 0
    if result == PipelineResult.CANCELLED:
        print("Backup was cancelled.", file=out)
        return 1
    if result in (
        PipelineResult.NO_BROWSERS_FOUND,
        PipelineResult.INSUFFICIENT_DISK_SPACE,
    ):
        return 1
    print(f"Backup failed. Reason: {result.name}", file=out)
    return 1


def _print_matches(
    matches: Dict[str, List[str]], formatted_size: str, quiet: bool
) -> None:
    """Format and display detected browser profile matches."""
    if not quiet:
        _print_banner("DETECTED BROWSER PROFILES")

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

    if not quiet:
        print("-" * 40)
        print(f"Total Profiles: {total_profiles}")
        print(f"Estimated Size: {formatted_size}")
        print("=" * 40)


def run_list(args: Optional[argparse.Namespace] = None) -> int:
    """List detected browser profiles without performing a backup.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code (0 for success, 1 on error).
    """
    from atlas.backup import size

    quiet = _is_quiet(args)
    if quiet:
        import logging

        logging.getLogger().setLevel(logging.ERROR)

    if not _verify_environment(quiet=quiet):
        return 1

    target = getattr(args, "browser", None) if args else None
    pipeline = Pipeline(target_browser=target)

    if target and not pipeline.browsers:
        out = sys.stderr if quiet else sys.stdout
        print(f"Error: No browser found matching '{target}'.", file=out)
        return 1

    try:
        matches = pipeline.scan_profiles()
    except KeyboardInterrupt:
        out = sys.stderr if quiet else sys.stdout
        print("\nScan cancelled by user.", file=out)
        return 1

    if not matches:
        out = sys.stderr if quiet else sys.stdout
        msg = (
            f"No profiles found on this system for '{target}'."
            if target
            else "No supported browser profiles found on this system."
        )
        print(msg, file=out)
        return 1 if quiet else 0

    try:
        total_bytes = pipeline.estimate_size(matches)
        formatted_size = size.format_size(total_bytes)
    except KeyboardInterrupt:
        out = sys.stderr if quiet else sys.stdout
        print("\nSize estimation cancelled by user.", file=out)
        return 1

    _print_matches(matches, formatted_size, quiet=quiet)
    return 0


def run_backup(args: Optional[argparse.Namespace] = None) -> int:
    """Execute the backup pipeline in CLI mode.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    quiet = _is_quiet(args)
    if quiet:
        import logging

        logging.getLogger().setLevel(logging.ERROR)

    _LOGGED_MILESTONES.clear()

    if not _verify_environment(quiet=quiet):
        return 1

    _print_banner("ATLAS CLI MODE", quiet=quiet)

    if not _apply_output_directory(args, quiet=quiet):
        return 1

    target = getattr(args, "browser", None) if args else None

    pipeline = Pipeline(
        progress_callback=None if quiet else _on_progress,
        scanned_callback=None if quiet else _on_scanned,
        estimated_callback=None if quiet else _on_estimated,
        no_browsers_found_callback=lambda: _on_no_browsers(target, quiet),
        disk_space_error_callback=lambda r, a: _on_disk_error(r, a, quiet),
        target_browser=target,
    )

    if target and not pipeline.browsers:
        out = sys.stderr if quiet else sys.stdout
        print(f"Error: No browser found matching '{target}'.", file=out)
        return 1

    if not quiet:
        print("Starting backup process...\n")

    try:
        result = pipeline.run()
    except KeyboardInterrupt:
        pipeline.cancel()
        clear_line()
        out = sys.stderr if quiet else sys.stdout
        print("\nBackup cancelled by user.", file=out)
        return 1
    except Exception as err:
        clear_line()
        out = sys.stderr if quiet else sys.stdout
        print(f"\nAn unexpected error occurred: {err}", file=out)
        return 1

    if not quiet:
        print()  # Final newline after progress completes
    return _handle_pipeline_result(result, quiet=quiet)


def run_cli(args: Optional[argparse.Namespace] = None) -> int:
    """Execute the requested command in CLI mode.

    Routes execution to the appropriate command handler based on parsed
    command-line arguments, defaulting to standard profile backup.

    Args:
        args: Parsed command-line arguments for future expandability.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    if args and getattr(args, "list", False):
        return run_list(args)
    return run_backup(args)
