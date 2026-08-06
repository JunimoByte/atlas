"""Atlas | Archive Management.

ZIP archive creation and compression utilities for Atlas.
Handles safe compression of browser profile directories with error handling.
"""

# =============================================================================
# IMPORTS
# =============================================================================

import itertools
import logging
import os
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, Iterable, Optional, Tuple, Union

from atlas.backup.attribute import create_zip_info
from atlas.backup.disk import relative_zip_path, safe_unlink
from atlas.backup.filter import scan_files
from atlas.lib.directories import get_downloads_dir

# =============================================================================
# LOGGING
# =============================================================================

LOGGER = logging.getLogger(__name__)

# =============================================================================
# CONSTANTS
# =============================================================================

CHUNK_SIZE = 64 * 1024
ATLAS_SUBDIR = "Backup"
ZIP_OUTPUT_DIR = None  # type: Optional[Path]

# =============================================================================
# FUNCTIONS
# =============================================================================


def _get_default_output_dir() -> Path:
    """Return the default output directory inside Downloads.

    The path is ``<Downloads>/Atlas`` where ``<Downloads>``
    is resolved by :func:`get_downloads_dir`.

    Returns:
        Path: Absolute path to the default output directory.

    """
    return get_downloads_dir() / ATLAS_SUBDIR


def get_zip_output_dir() -> Path:
    """Return the resolved ZIP output directory.

    The directory is lazily initialised on the first call
    and created if it does not already exist.

    Returns:
        Path: Absolute path to the ZIP output directory.

    """
    global ZIP_OUTPUT_DIR  # noqa: WPS420

    if ZIP_OUTPUT_DIR is None:
        ZIP_OUTPUT_DIR = _get_default_output_dir()

    output_dir = ZIP_OUTPUT_DIR.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def generate_zip_name() -> str:
    """Generate a timestamped zip filename."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    return "Unknown_{}.zip".format(timestamp)


def _is_within_output_dir(path: Path, output_dir: Path) -> bool:
    """Return True if a resolved path stays within the output directory.

    Args:
        path: Resolved candidate archive path.
        output_dir: Resolved output directory path.

    Returns:
        bool: True if path is contained within output_dir.

    """
    try:
        path.relative_to(output_dir)
        return True
    except ValueError:
        return False


def _resolve_output_zip_path(zip_name: str) -> Path:
    """Resolve and validate the final ZIP output path.

    Ensure the final archive path remains within the configured output
    directory, even if the provided ZIP name contains traversal elements
    or an absolute path.

    Args:
        zip_name: Requested ZIP file name.

    Returns:
        Path: Validated absolute path for the ZIP archive.

    Raises:
        ValueError: If the resolved path escapes the output directory.

    """
    output_dir = get_zip_output_dir()
    zip_path = (output_dir / zip_name).resolve()

    if not _is_within_output_dir(zip_path, output_dir):
        raise ValueError(
            "ZIP path escapes the output directory: {}".format(zip_name)
        )

    return zip_path


def _write_file_to_zip(
    zip_file: zipfile.ZipFile,
    file_path: Path,
    zip_info: zipfile.ZipInfo,
    cancel_callback: Optional[Callable[[], bool]] = None,
) -> bool:
    """Write a single file to the ZIP archive.

    Args:
        zip_file: Open ZipFile object.
        file_path: Path to the source file.
        zip_info: ZipInfo object for the file.
        cancel_callback: Optional cancellation check.

    Returns:
        bool: True if written successfully, False if cancelled or skipped
            due to an access/permission error.

    Raises:
        Exception: Re-raises any unexpected error so the caller can treat
            it as a fatal archive failure.

    """
    try:
        with file_path.open("rb") as src_file:
            with zip_file.open(zip_info, "w") as dest_file:
                read = src_file.read
                while True:
                    chunk = read(CHUNK_SIZE)
                    if not chunk:
                        break
                    if cancel_callback and cancel_callback():
                        return False
                    dest_file.write(chunk)
        return True
    except OSError as error:
        LOGGER.warning(
            "Skipped (I/O error / file in use): {} - {}".format(
                file_path, error
            )
        )
        return False
    except Exception:
        raise


def _unique_sources(sources: Iterable[Path]) -> list:
    """Return existing directory sources once, preserving their order."""
    unique_sources = []
    seen_sources = set()

    for source in sources:
        resolved_source = source.resolve()
        source_key = os.path.normcase(str(resolved_source))

        if (
            resolved_source.exists()
            and resolved_source.is_dir()
            and source_key not in seen_sources
        ):
            seen_sources.add(source_key)
            unique_sources.append(resolved_source)

    return unique_sources


def _archive_root_names(sources: Iterable[Path]) -> Dict[Path, str]:
    """Assign unique top-level archive names to source directories.

    Keep each source directory's actual name where possible.  Only a source
    whose name already exists in the archive receives a ``(1)``, ``(2)``,
    and so on suffix.  This keeps arbitrary profile folder names intact while
    preventing duplicate entries from separately discovered installations.
    """
    archive_root_names = {}
    used_names = set()

    for source in sources:
        source_name = source.name
        archive_name = source_name
        suffix = 1

        while archive_name.casefold() in used_names:
            archive_name = "{}({})".format(source_name, suffix)
            suffix += 1

        archive_root_names[source] = archive_name
        used_names.add(archive_name.casefold())

    return archive_root_names


def write_zip(
    files: Iterable[Tuple[Path, Path]],
    zip_path: Path,
    cancel_callback: Optional[Callable[[], bool]] = None,
    archive_root_names: Optional[Dict[Path, str]] = None,
) -> None:
    """Write files to a ZIP archive safely.

    Handle large files, preserve timestamps, and set permissions.

    Args:
        files (Iterable[Tuple[Path, Path]]): Iterable of (source_root,
            file_path) pairs. The source_root is used to compute
            relative archive paths.
        zip_path (Path): Destination path for the ZIP archive.
        cancel_callback (Optional[Callable[[], bool]]): Function to
            check for cancellation.
        archive_root_names (Optional[Dict[Path, str]]): Archive directory
            name assigned to each source root.

    Raises:
        RuntimeError: If a file cannot be written safely to the archive.

    """
    temp_zip_path = zip_path.with_suffix(".zip.tmp")
    archive_created = False

    try:
        with zipfile.ZipFile(
            temp_zip_path,
            "w",
            zipfile.ZIP_DEFLATED,
            allowZip64=True,
            strict_timestamps=False,
        ) as zip_file:
            for base_path, file_path in files:
                if cancel_callback and cancel_callback():
                    return

                try:
                    rel_path = relative_zip_path(file_path, base_path)
                    archive_root_name = (
                        archive_root_names.get(base_path)
                        if archive_root_names
                        else None
                    )
                    if archive_root_name:
                        _, relative_file_path = rel_path.split("/", 1)
                        rel_path = "{}/{}".format(
                            archive_root_name, relative_file_path
                        )
                    zip_info = create_zip_info(file_path)
                    zip_info.filename = rel_path

                    # Write file contents to ZIP.
                    # Returns False only for cancellation or access errors
                    # (both are safe to skip). Unexpected failures raise.
                    did_write = _write_file_to_zip(
                        zip_file, file_path, zip_info, cancel_callback
                    )
                    if not did_write:
                        if cancel_callback and cancel_callback():
                            return
                        continue

                except Exception as error:
                    LOGGER.warning(
                        "Unexpected error processing {}: {}".format(
                            file_path, error
                        )
                    )
                    raise

        # Validate and finalize
        if not temp_zip_path.exists() or temp_zip_path.stat().st_size == 0:
            raise RuntimeError(
                "Zip creation produced an empty or missing archive"
            )

        os.replace(temp_zip_path, zip_path)
        archive_created = True
        LOGGER.info("Zip archive created: {}".format(zip_path))
    finally:
        if not archive_created:
            safe_unlink(temp_zip_path)


# =============================================================================
# MAIN API
# =============================================================================


def compress(  # noqa: C901
    source: Union[str, Path, list],
    zip_name: Optional[str] = None,
    cancel_callback: Optional[Callable[[], bool]] = None,
) -> Optional[Path]:
    """Compress one or multiple directories into a ZIP archive safely.

    Args:
        source (Union[str, Path, list]): Directory path(s) to compress.
        zip_name (Optional[str]): Name of the output ZIP file.
        cancel_callback (Optional[Callable[[], bool]]): Function to
            check for cancellation.

    Returns:
        Optional[Path]: Path to the created ZIP archive, or None if failed.

    """
    # Normalize sources
    if isinstance(source, (str, Path)):
        sources = [Path(source)]
    elif isinstance(source, list):
        sources = [Path(s) for s in source]
    else:
        LOGGER.error("Invalid source type. Must be path or list of paths.")
        return None

    sources = _unique_sources(sources)
    if not sources:
        LOGGER.warning("No valid source paths found. Halting.")
        raise FileNotFoundError("No valid source paths found.")

    # Handle zip filename
    if not zip_name or not isinstance(zip_name, str):
        zip_name = generate_zip_name()
        LOGGER.warning(
            "No valid zip name provided. Generated: {}".format(zip_name)
        )

    try:
        zip_path = _resolve_output_zip_path(zip_name)
    except ValueError as error:
        LOGGER.error("Invalid zip output path: %s", error)
        return None

    try:
        valid_files_gen = scan_files(sources, cancel_callback)
        try:
            first_root, first_file = next(valid_files_gen)
        except StopIteration:
            if cancel_callback and cancel_callback():
                LOGGER.info("Compression cancelled during scanning.")
                return None
            LOGGER.warning("No files to compress after scanning.")
            raise FileNotFoundError("No files to compress after scanning.")

        valid_files = itertools.chain(
            [(first_root, first_file)], valid_files_gen
        )
        write_zip(
            valid_files,
            zip_path,
            cancel_callback,
            _archive_root_names(sources),
        )

        if cancel_callback and cancel_callback():
            LOGGER.info("Compression cancelled during writing.")
            safe_unlink(zip_path)
            return None

        return zip_path

    except FileNotFoundError:
        # Re-raise so the pipeline can gracefully skip this archive
        raise
    except Exception as error:
        LOGGER.error("Failed to create zip archive: {}".format(error))
        temp_zip_path = zip_path.with_suffix(".zip.tmp")
        safe_unlink(temp_zip_path)
        return None
