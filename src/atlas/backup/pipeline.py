"""Atlas | Pipeline.

Handles the workflow for scanning browser profiles, estimating sizes,
and compressing them into ZIP archives.

Designed for modular testing and separation from PyQt signals.
"""

# =============================================================================
# IMPORTS
# =============================================================================

import gc
import logging
import platform
import time
from collections import defaultdict
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from atlas.backup import archive
from atlas.backup import profile as Profile  # noqa: N812
from atlas.backup import size as Size  # noqa: N812
from atlas.backup.size import ScanError, ScanTimeoutError
from atlas.lib import browsers

# =============================================================================
# LOGGING
# =============================================================================

LOGGER = logging.getLogger(__name__)

# =============================================================================
# CONSTANTS
# =============================================================================

MAX_RETRIES = 3
RETRY_DELAY = 1.0
SIGNAL_BATCH_INTERVAL = 0.5
PROGRESS_BATCH_INTERVAL = 0.25


class _ProgressTracker:
    """Rate-limited byte progress calculator for backup archives."""

    def __init__(
        self,
        total_bytes: int,
        emit_fn: Callable[[int, int], None],
        interval: float = PROGRESS_BATCH_INTERVAL,
    ) -> None:
        self.total_bytes = total_bytes
        self.emit_fn = emit_fn
        self.interval = interval
        self.bytes_base = 0
        self.current_browser_bytes = 0
        self.last_emit_time = 0.0
        self.last_emit_pct = -1

    def make_chunk_callback(self) -> Optional[Callable[[int], None]]:
        """Return a chunk callback for an archive compression attempt."""
        if self.total_bytes <= 0:
            return None

        self.current_browser_bytes = 0

        def on_chunk(chunk_len: int) -> None:
            self.current_browser_bytes += chunk_len
            now = time.monotonic()
            if now - self.last_emit_time < self.interval:
                return
            total_so_far = self.bytes_base + self.current_browser_bytes
            pct = min(
                99, max(0, int((total_so_far / self.total_bytes) * 100))
            )
            if pct > self.last_emit_pct:
                self.last_emit_time = now
                self.last_emit_pct = pct
                self.emit_fn(pct, 100)

        return on_chunk

    def on_browser_finished(
        self, completed: int, total: int
    ) -> Optional[Tuple[int, int]]:
        """Commit browser bytes and compute monotonic progress update."""
        self.bytes_base += self.current_browser_bytes
        self.current_browser_bytes = 0

        if self.total_bytes <= 0:
            return (completed, total)

        if completed == total:
            return (completed, total)

        pct = min(
            99,
            max(
                self.last_emit_pct,
                int((self.bytes_base / self.total_bytes) * 100),
            ),
        )
        if pct > self.last_emit_pct:
            self.last_emit_pct = pct
            return (pct, 100)
        return None


# =============================================================================
# CLASSES
# =============================================================================


class PipelineResult(Enum):
    """Describe the final outcome of a pipeline run."""

    SUCCESS = "success"
    CANCELLED = "cancelled"
    NO_BROWSERS_FOUND = "no_browsers_found"
    INSUFFICIENT_DISK_SPACE = "insufficient_disk_space"
    FAILED = "failed"


class Pipeline:
    """Executes the scanning, size estimation, and backup workflow.

    Designed to be PyQt-agnostic and testable.
    """

    def __init__(
        self,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        scanned_callback: Optional[Callable[[str], None]] = None,
        estimated_callback: Optional[Callable[[str], None]] = None,
        no_browsers_found_callback: Optional[Callable[[], None]] = None,
        disk_space_error_callback: Optional[Callable[[str, str], None]] = None,
        target_browser: Optional[str] = None,
    ) -> None:
        """Initialize the Pipeline.

        Args:
            progress_callback: Callback for backup progress.
            scanned_callback: Callback for text status updates.
            estimated_callback: Callback for estimated size.
            no_browsers_found_callback: Callback when no profiles are found.
            disk_space_error_callback: Callback for insufficient disk space.
            target_browser: Optional specific browser name filter.

        """
        self._cancelled = False
        self._cancel_logged = False
        self.progress_callback = progress_callback
        self.scanned_callback = scanned_callback
        self.estimated_callback = estimated_callback
        self.no_browsers_found_callback = no_browsers_found_callback
        self.disk_space_error_callback = disk_space_error_callback
        self.target_browser = target_browser
        self.created_archives: List[Path] = []
        self._total_bytes: int = 0

        all_browsers = browsers.grab()
        if target_browser and target_browser.strip():
            normalized = target_browser.strip().casefold()
            matched = {
                k: v
                for k, v in all_browsers.items()
                if k.casefold() == normalized
            }
            if not matched:
                matched = {
                    k: v
                    for k, v in all_browsers.items()
                    if normalized in k.casefold()
                }
            self.browsers = matched
        else:
            self.browsers = all_browsers

    def __repr__(self) -> str:
        """Return a string representation of the Pipeline."""
        return f"<Pipeline(cancelled={self._cancelled})>"

    # =========================================================================
    # CANCELLATION & SIGNALS
    # =========================================================================

    def cancel(self) -> None:
        """Mark the pipeline as cancelled."""
        if not self._cancelled:
            LOGGER.info("Pipeline cancellation requested")
            self._cancelled = True

    def is_cancelled(self) -> bool:
        """Return True if cancellation was requested."""
        if not self._cancelled:
            return False

        if not self._cancel_logged:
            LOGGER.info("Pipeline thread acknowledged cancellation.")
            self._cancel_logged = True

        return True

    def _cooperative_sleep(self, seconds: float) -> bool:
        """Sleep in small increments to remain responsive to cancellation.

        Returns True if cancelled during sleep, False otherwise.
        """
        steps = int(seconds * 10)
        for _ in range(steps):
            if self.is_cancelled():
                return True
            time.sleep(0.1)
        return False

    def _emit(self, callback: Optional[Callable], *args: Any) -> None:
        """Safely emit a signal callback if it exists."""
        if callback:
            callback(*args)

    # =========================================================================
    # HELPERS
    # =========================================================================

    def _retry_operation(
        self, operation: Callable, *args: Any, **kwargs: Any
    ) -> Any:
        """Retry a given operation up to MAX_RETRIES with exponential backoff.

        Only transient errors (like general OSErrors) are retried. Logic errors
        and definitive system errors (PermissionError, FileNotFoundError)
        immediately raise.

        Raises:
            Exception: The last exception encountered if all retries fail,
                       or immediately if the exception is not in the retry
                       allowlist.
        """
        for attempt in range(MAX_RETRIES):
            if self.is_cancelled():
                return None

            try:
                return operation(*args, **kwargs)
            except (ScanTimeoutError, ScanError, InterruptedError) as error:
                LOGGER.debug(
                    "Non-retryable operational error on attempt %d: %s",
                    attempt + 1,
                    error,
                )
                raise
            except OSError as error:
                if isinstance(error, (PermissionError, FileNotFoundError)):
                    LOGGER.debug(
                        "Non-retryable OSError on attempt %d: %s",
                        attempt + 1,
                        error,
                    )
                    raise

                if attempt < MAX_RETRIES - 1:
                    wait_time = RETRY_DELAY * (2**attempt)
                    LOGGER.warning(
                        "Attempt %d failed: %s. Retrying in %ss...",
                        attempt + 1,
                        error,
                        wait_time,
                    )
                    if self._cooperative_sleep(wait_time):
                        return None
                else:
                    LOGGER.error(
                        "All %d attempts failed. Last error: %s",
                        MAX_RETRIES,
                        error,
                    )
                    raise
        return None

    # =========================================================================
    # CORE METHODS
    # =========================================================================

    def run(self) -> PipelineResult:
        """Execute the complete backup pipeline workflow.

        Returns:
            PipelineResult: Final outcome of the backup workflow.

        """
        LOGGER.info("Pipeline started")

        matches = self.scan_profiles()
        if self.is_cancelled():
            return PipelineResult.CANCELLED
        if not matches:
            return PipelineResult.NO_BROWSERS_FOUND

        total_size = self.estimate_size(matches)
        if self.is_cancelled():
            return PipelineResult.CANCELLED

        if not self._verify_disk_space(total_size):
            return PipelineResult.INSUFFICIENT_DISK_SPACE
        if self.is_cancelled():
            return PipelineResult.CANCELLED

        if not self.perform_backup(matches):
            if self.is_cancelled():
                return PipelineResult.CANCELLED
            LOGGER.error("Pipeline finished with backup errors.")
            return PipelineResult.FAILED

        LOGGER.info("Pipeline complete.")
        return PipelineResult.SUCCESS

    def _verify_disk_space(self, total_size: int) -> bool:
        """Validate if target disk has capacity for backup."""
        if total_size < 0:
            LOGGER.error(
                "Disk space check skipped: size estimate is unreliable."
            )
            self._emit(
                self.disk_space_error_callback,
                "Unknown",
                "Unknown",
            )
            return False

        has_space, available_space = Size.check_disk_space(total_size)
        if not has_space:
            self._emit(
                self.disk_space_error_callback,
                Size.format_size(total_size),
                available_space,
            )
            return False
        return True

    def scan_profiles(self) -> Dict[str, List[str]]:
        """Scan for browser profiles."""
        os_name = platform.system().lower()
        browser_matches = defaultdict(list)
        total = len(self.browsers)
        scanned = 0
        last_emit_time = time.monotonic()

        self._emit(self.scanned_callback, "preparing...")

        for browser in self.browsers:
            if self.is_cancelled():
                return {}

            try:
                profiles = self._retry_operation(
                    Profile.find_profile,
                    browser,
                    os_name,
                    browsers_data=self.browsers,
                )

                if profiles:
                    browser_matches[browser].extend(profiles)
            except Exception:
                LOGGER.exception("Error scanning %s", browser)
            finally:
                scanned += 1
                now = time.monotonic()
                if now - last_emit_time >= SIGNAL_BATCH_INTERVAL:
                    self._emit(
                        self.scanned_callback, f"{scanned} / {total} scanned"
                    )
                    last_emit_time = now

        self._emit(self.scanned_callback, f"{scanned} / {total} scanned")

        if (
            not browser_matches
            or sum(len(p) for p in browser_matches.values()) == 0
        ):
            self._emit(self.no_browsers_found_callback)
            return {}

        return browser_matches

    def estimate_size(self, browser_matches: Dict[str, List[str]]) -> int:
        """Estimate total size of profiles in bytes.

        Sizes are cached per unique path to avoid scanning the same folder
        multiple times, but the final sum accounts for shared paths being
        written to multiple ZIP archives.
        """
        all_paths = [
            p for paths in browser_matches.values() for p in paths if p
        ]
        total_profiles = len(all_paths)
        processed = 0
        total_size = 0
        last_emit_time = time.monotonic()
        path_size_cache: Dict[str, int] = {}

        for path_str in all_paths:
            if self.is_cancelled():
                return total_size

            try:
                if path_str not in path_size_cache:
                    size = self._retry_operation(
                        Size.get_directory_size, path_str, self.is_cancelled
                    )
                    path_size_cache[path_str] = size
                else:
                    size = path_size_cache[path_str]

                if size is not None:
                    total_size += size
            except ScanTimeoutError as error:
                LOGGER.error(
                    "Size scan timed out for %s: %s. "
                    "Estimate is unreliable, blocking "
                    "disk check.",
                    path_str,
                    error,
                )
                return -1
            except ScanError as error:
                LOGGER.warning(
                    "Size scan incomplete for %s: %s. "
                    "Skipping this path.",
                    path_str,
                    error,
                )
            except Exception as error:
                LOGGER.error(
                    "Could not calculate size for %s: %s", path_str, error
                )
            finally:
                processed += 1
                now = time.monotonic()
                if now - last_emit_time >= SIGNAL_BATCH_INTERVAL:
                    self._emit(
                        self.scanned_callback,
                        f"{processed} / {total_profiles} indexed",
                    )
                    last_emit_time = now

        self._emit(
            self.scanned_callback, f"{processed} / {total_profiles} indexed"
        )

        formatted_size = Size.format_size(total_size)

        LOGGER.info("Estimated total size: %s", formatted_size)
        self._emit(self.estimated_callback, formatted_size)
        self._total_bytes = max(0, total_size)

        return total_size

    def perform_backup(self, browser_matches: Dict[str, List[str]]) -> bool:
        """Compress profiles into ZIP archives.

        Note: browser_matches keys are unique browser names.

        Returns:
            bool: True if every archive is created successfully.

        """
        self.created_archives = []
        total = len(browser_matches)
        completed = 0
        backup_succeeded = True
        tracker = _ProgressTracker(
            getattr(self, "_total_bytes", 0),
            lambda cur, tot: self._emit(self.progress_callback, cur, tot),
        )

        for browser_name, paths in browser_matches.items():
            if self.is_cancelled():
                return False

            try:
                zip_name = f"{browser_name}.zip"
                LOGGER.info(
                    "Creating archive: %s for %d path(s)", zip_name, len(paths)
                )

                # Check cancelled immediately before expensive operation
                if self.is_cancelled():
                    return False

                result = self._retry_operation(
                    archive.compress,
                    paths,
                    zip_name,
                    cancel_callback=self.is_cancelled,
                    progress_callback=tracker.make_chunk_callback(),
                )
                gc.collect()

                if result is not None:
                    self.created_archives.append(result)
                    LOGGER.info("Archive created: %s", zip_name)
                elif not self._cancelled:
                    backup_succeeded = False
                    LOGGER.error("Failed to create archive: %s", zip_name)

            except FileNotFoundError as error:
                backup_succeeded = False
                LOGGER.warning("Skipped archive %s: %s", zip_name, error)
            except Exception:
                backup_succeeded = False
                LOGGER.exception("Error zipping %s", browser_name)
            finally:
                completed += 1
                prog = tracker.on_browser_finished(completed, total)
                if prog is not None:
                    self._emit(self.progress_callback, prog[0], prog[1])

        return backup_succeeded
