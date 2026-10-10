"""Atlas | CLI Entry Point.

Provides a clean, terminal-friendly interface for running Atlas backups
without invoking the PyQt GUI. Useful for pure terminal environments
(bash, zsh, fish).
"""

# =============================================================================
# IMPORTS
# =============================================================================

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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


def _is_json(args: Optional[argparse.Namespace]) -> bool:
    """Return True if JSON output was requested."""
    return bool(args and getattr(args, "json", False))


def _is_verify(args: Optional[argparse.Namespace]) -> bool:
    """Return True if archive verification was requested."""
    return bool(args and getattr(args, "verify", False))


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


def _emit_json(data: Dict[str, Any]) -> None:
    """Print structured JSON payload to standard output."""
    print(json.dumps(data, indent=2))


def _emit_json_error(status: str, message: str) -> None:
    """Print error payload in JSON format."""
    _emit_json({"status": status, "message": message})


def _emit_list_json(
    matches: Dict[str, List[str]],
    total_bytes: int,
    formatted_size: str,
    status: str = "success",
) -> None:
    """Format and display detected browser profiles as JSON."""
    data = {
        "status": status,
        "total_profiles": sum(len(p) for p in matches.values()),
        "total_bytes": total_bytes,
        "formatted_size": formatted_size,
        "browsers": {
            browser: sorted(paths)
            for browser, paths in sorted(matches.items())
            if paths
        },
    }
    _emit_json(data)


def _verify_archives(
    archives: List[Path],
    quiet: bool = False,
    silent: bool = False,
) -> Tuple[bool, Dict[Path, Tuple[bool, Optional[str], int]]]:
    """Verify integrity of created archives via CRC-32 checksums.

    Returns:
        Tuple of (all_valid, results_dict).
    """
    from atlas.backup.archive import verify_archive

    results: Dict[Path, Tuple[bool, Optional[str], int]] = {}
    all_valid = True

    for archive_path in archives:
        arc = (
            Path(archive_path)
            if not isinstance(archive_path, Path)
            else archive_path
        )
        is_valid, corrupt, count = verify_archive(arc)
        results[arc] = (is_valid, corrupt, count)
        if not is_valid:
            all_valid = False
            if not silent:
                out = sys.stderr if quiet else sys.stdout
                err_msg = corrupt or "Corrupted archive"
                print(
                    f"[Verify] {arc.name}: FAILED ({err_msg})",
                    file=out,
                )
        elif not quiet and not silent:
            print(
                f"[Verify] {arc.name}: "
                f"OK (CRC-32 verified, {count} files)"
            )

    return all_valid, results


def _emit_backup_json(
    archives: List[Path],
    status: str,
    verified_results: Optional[
        Dict[Path, Tuple[bool, Optional[str], int]]
    ] = None,
) -> None:
    """Format and emit backup execution results as JSON."""
    from atlas.backup import size

    archives_data = []
    for arc in archives:
        arc_path = Path(arc) if not isinstance(arc, Path) else arc
        try:
            size_bytes = (
                arc_path.stat().st_size if arc_path.is_file() else 0
            )
        except OSError:
            size_bytes = 0
        arc_info: Dict[str, Any] = {
            "archive": str(arc_path),
            "name": arc_path.name,
            "size_bytes": size_bytes,
            "formatted_size": size.format_size(size_bytes),
        }
        if verified_results is not None:
            res = verified_results.get(arc_path) or verified_results.get(arc)
            if res is not None:
                is_valid, corrupt, count = res
                arc_info["verified"] = is_valid
                arc_info["file_count"] = count
                if not is_valid:
                    arc_info["error"] = corrupt
        archives_data.append(arc_info)

    data = {
        "status": status,
        "total_archives": len(archives_data),
        "archives": archives_data,
    }
    _emit_json(data)


def _report_error(
    msg: str,
    status: str = "error",
    is_json: bool = False,
    quiet: bool = False,
) -> None:
    """Report an error message to JSON output or standard output."""
    if is_json:
        _emit_json_error(status, msg.strip())
    else:
        out = sys.stderr if quiet else sys.stdout
        print(msg, file=out)


def _init_cli_env(is_json: bool, quiet: bool) -> bool:
    """Initialize logging and verify system browser environment."""
    if quiet:
        import logging

        logging.getLogger().setLevel(logging.ERROR)
    if not _verify_environment(quiet=quiet):
        if is_json:
            _emit_json_error(
                "error", "Failed to load browser configuration."
            )
        return False
    return True


def _scan_profiles(
    pipeline: Pipeline, is_json: bool, quiet: bool
) -> Optional[Dict[str, List[str]]]:
    """Scan browser profiles with interrupt handling."""
    try:
        return pipeline.scan_profiles()
    except KeyboardInterrupt:
        _report_error(
            "\nScan cancelled by user.",
            status="cancelled",
            is_json=is_json,
            quiet=quiet,
        )
        return None
    except Exception as err:
        _report_error(
            f"\nAn unexpected error occurred during scan: {err}",
            status="error",
            is_json=is_json,
            quiet=quiet,
        )
        return None


def _handle_empty_matches(
    target: Optional[str], is_json: bool, quiet: bool
) -> int:
    """Handle empty profile match results."""
    if is_json:
        _emit_list_json({}, 0, "0 B", status="no_browsers_found")
        return 0
    msg = (
        f"No profiles found on this system for '{target}'."
        if target
        else "No supported browser profiles found on this system."
    )
    _report_error(msg, is_json=False, quiet=quiet)
    return 1 if quiet else 0


def _estimate_matches_size(
    pipeline: Pipeline,
    matches: Dict[str, List[str]],
    is_json: bool,
    quiet: bool,
) -> Optional[Tuple[int, str]]:
    """Estimate total size of matched profiles with interrupt handling."""
    from atlas.backup import size

    try:
        total_bytes = pipeline.estimate_size(matches)
        return total_bytes, size.format_size(total_bytes)
    except KeyboardInterrupt:
        _report_error(
            "\nSize estimation cancelled by user.",
            status="cancelled",
            is_json=is_json,
            quiet=quiet,
        )
        return None
    except Exception as err:
        _report_error(
            f"\nAn unexpected error occurred during sizing: {err}",
            status="error",
            is_json=is_json,
            quiet=quiet,
        )
        return None


def run_list(args: Optional[argparse.Namespace] = None) -> int:
    """List detected browser profiles without performing a backup.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code (0 for success, 1 on error).
    """
    is_json = _is_json(args)
    quiet = _is_quiet(args) or is_json
    if not _init_cli_env(is_json, quiet):
        return 1

    raw_target = getattr(args, "browser", None) if args else None
    target = raw_target.strip() if raw_target else None
    pipeline = Pipeline(target_browser=target)
    if target and not pipeline.browsers:
        _report_error(
            f"Error: No browser found matching '{target}'.",
            is_json=is_json,
            quiet=quiet,
        )
        return 1

    matches = _scan_profiles(pipeline, is_json, quiet)
    if matches is None:
        return 1
    if not matches:
        return _handle_empty_matches(target, is_json, quiet)

    est = _estimate_matches_size(pipeline, matches, is_json, quiet)
    if est is None:
        return 1

    total_bytes, formatted_size = est
    if is_json:
        _emit_list_json(matches, total_bytes, formatted_size)
    else:
        _print_matches(matches, formatted_size, quiet=quiet)
    return 0


def _create_backup_pipeline(
    target: Optional[str], quiet: bool, is_json: bool
) -> Pipeline:
    """Construct Pipeline instance with appropriate CLI callbacks."""
    return Pipeline(
        progress_callback=None if quiet else _on_progress,
        scanned_callback=None if quiet else _on_scanned,
        estimated_callback=None if quiet else _on_estimated,
        no_browsers_found_callback=(
            None if is_json else (lambda: _on_no_browsers(target, quiet))
        ),
        disk_space_error_callback=(
            None if is_json else (lambda r, a: _on_disk_error(r, a, quiet))
        ),
        target_browser=target,
    )


def _execute_pipeline_safely(
    pipeline: Pipeline, is_json: bool, quiet: bool
) -> Optional[PipelineResult]:
    """Execute pipeline run catching interrupts and unexpected errors."""
    try:
        return pipeline.run()
    except KeyboardInterrupt:
        pipeline.cancel()
        clear_line()
        _report_error(
            "\nBackup cancelled by user.",
            status="cancelled",
            is_json=is_json,
            quiet=quiet,
        )
        return None
    except Exception as err:
        clear_line()
        _report_error(
            f"\nAn unexpected error occurred: {err}",
            status="error",
            is_json=is_json,
            quiet=quiet,
        )
        return None


def _finalize_backup(
    pipeline: Pipeline,
    result: PipelineResult,
    is_verify: bool,
    is_json: bool,
    quiet: bool,
) -> int:
    """Validate archives if requested and emit final output."""
    verified_results = None
    verify_ok = True
    if (
        is_verify
        and result == PipelineResult.SUCCESS
        and pipeline.created_archives
    ):
        verify_ok, verified_results = _verify_archives(
            pipeline.created_archives,
            quiet=quiet,
            silent=is_json,
        )

    if is_json:
        status = result.value
        if result == PipelineResult.SUCCESS and not verify_ok:
            status = "verification_failed"
        _emit_backup_json(
            pipeline.created_archives,
            status=status,
            verified_results=verified_results,
        )
        return 0 if (result == PipelineResult.SUCCESS and verify_ok) else 1

    if result == PipelineResult.SUCCESS and not verify_ok:
        out = sys.stderr if quiet else sys.stdout
        print("Error: Post-backup verification failed.", file=out)
        return 1

    return _handle_pipeline_result(result, quiet=quiet)


def run_backup(args: Optional[argparse.Namespace] = None) -> int:
    """Execute the backup pipeline in CLI mode.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    is_json = _is_json(args)
    is_verify = _is_verify(args)
    quiet = _is_quiet(args) or is_json

    _LOGGED_MILESTONES.clear()
    if not _init_cli_env(is_json, quiet):
        return 1

    _print_banner("ATLAS CLI MODE", quiet=quiet)
    if not _apply_output_directory(args, quiet=quiet):
        if is_json:
            out_arg = getattr(args, "output", "")
            _emit_json_error(
                "error", f"Invalid output directory '{out_arg}'."
            )
        return 1

    raw_target = getattr(args, "browser", None) if args else None
    target = raw_target.strip() if raw_target else None
    pipeline = _create_backup_pipeline(target, quiet, is_json)
    if target and not pipeline.browsers:
        _report_error(
            f"Error: No browser found matching '{target}'.",
            is_json=is_json,
            quiet=quiet,
        )
        return 1

    if not quiet:
        print("Starting backup process...\n")

    result = _execute_pipeline_safely(pipeline, is_json, quiet)
    if result is None:
        return 1

    if not quiet:
        print()

    return _finalize_backup(
        pipeline, result, is_verify, is_json, _is_quiet(args)
    )


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
