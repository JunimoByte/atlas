# Architecture

## High-Level Flow

```text
Application Start
  → Permission Validation
  → Configuration Validation
  → UI Initialization
  → Theme Application
  → Idle State
  → Scan Profiles
  → Estimate Size
  → Disk Space Check
  → Archive Creation
  → Completion / Error
```

All validation steps occur before any disk-intensive or long-running operations begin.

---

## Trust Model

Atlas follows a strict, defensive trust model:

- **No elevated privileges**
  - The application must not run as admin/root.
  - Elevated execution is detected and explicitly rejected.

- **Read-only browser access**
  - Browser profiles are never modified.
  - No files are written to browser directories.

- **User-controlled output**
  - Archives are created only in user-selected locations.
  - No background writes or hidden destinations.

- **Safe file handling**
  - Symlinks, system files, and blacklisted paths are excluded.
  - Archive contents are sanitized to prevent traversal or metadata abuse.

- **Offline-first**
  - No network access, telemetry, or external calls at runtime.

---

## Entry Point

### `src/atlas/main.py`
The application's main entry point. Can be run via `python -m atlas.main` or the `atlas` command installed by `pyproject.toml`.

It orchestrates the startup sequence:

1. **Permission Validation**  
   Calls `permissions.is_elevated()`. If true, calls `permissions.show_elevated_permissions_dialog()` and exits.

2. **Configuration Verification**  
   Calls `browsers.verify_entries()`. Exits early if configuration is invalid.

3. **UI Initialization**  
   Instantiates `QApplication` and the main `Window`.

4. **Theme Application**  
   Calls `themes.initialize(win)` to set the icon, backdrop, and system theme.

5. **Execution**  
   Starts the PyQt event loop via `app.exec()`.

---

## Modules

### Display
Handles the visual components, window management, and interaction logic.

#### `display/window.py`
Defines the `Window` class (extends `QDialog`), the main application window.

- **UI Modes**: Manages visibility using the `UIMode` enum (`IDLE`, `SCANNING`, `COMPLETED`, `ERROR`) via `_set_ui_mode()`.
- **Mode Config**: `UI_MODE_CONFIG` declaratively maps each mode to visible elements and button configurations.
- **Signal Connection**: `_connect_signals()` maps global `Signals` events to UI handlers (`_on_backup_started`, `complete`, `_handle_disk_space_error`, `_handle_no_browsers`, etc.).
- **Delegation**: Delegates all business logic to `Controller`. The `scan()` method calls `controller.start_backup()`.
- **Progress**: `_update_progress()` converts current/total to a percentage for the progress bar.
- **Elapsed Time**: `_update_elapsed_time()` formats and updates the elapsed time label via `controls.format_elapsed_time()`, including scan status context.
- **Linux Compat**: `_setup_buttons()` strips icons from `QDialogButtonBox` buttons for Linux compatibility.

#### `display/controller.py`
Defines `Controller(QObject)`. Orchestrates the backup operation and worker lifecycle.

- **FSM State**: Tracks execution using `ControllerState` (`IDLE`, `RUNNING`, `SUCCESS`, `EMPTY`, `BLOCKED`, `CANCELLING`, `FAILED`). Terminal constraints handle graceful degradation without falsely indicating crashes.
- **Start**: `start_backup()` transitions to `RUNNING`, emits `backup_started`, starts the elapsed timer, and calls `_deploy_worker()`.
- **Cancel**: `cancel_backup()` transitions to `CANCELLING`, stops the timer, and explicitly requests worker shutdown.
- **Cleanup**: `cleanup()` is called on window close to stop any running thread and timer.
- **Worker Deployment**: `_deploy_worker()` creates a `Backup.Worker`, moves it to a `QThread`, connects its signals, and starts the thread.
- **Worker Termination**: `_request_worker_shutdown()` handles graceful cancellation, waits for the thread to exit, and terminates hung threads to prevent zombie processes.
- **State Guarding**: `_handle_worker_completion()` checks that the FSM is in the `RUNNING` state before transitioning to `SUCCESS` to prevent stale `done` signals from reverting `EMPTY` or `BLOCKED` states.
- **Elapsed Timer**: `_start_elapsed_timer()` / `_stop_elapsed_timer()` manage a `QTimer` that fires `_tick()` every `UPDATE_INTERVAL_MS` (300ms), emitting `elapsed_time` via `signals`.

#### `display/signals.py`
Defines `Signals(QObject)` — the event contract between `Controller` and `Window`.

| Signal | Payload | Description |
|--------|---------|-------------|
| `backup_started` | — | Backup process has started |
| `backup_finished` | — | Backup completed successfully |
| `backup_cancelled` | — | Backup was cancelled by the user |
| `progress` | `int, int` | Current and total archive count |
| `estimated_size` | `str` | Formatted total profile size |
| `scanned_entries` | `str` | Scan status text (e.g. `"42 / 250 scanned"`) |
| `elapsed_time` | `int` | Seconds elapsed since backup started |
| `disk_space_error` | `str, str` | Required and available space strings |
| `no_browsers_found` | — | No supported browsers detected |

#### `display/controls.py`
UI helper functions used by `Window`.

- **`set_text(button_box, name, text)`** — Sets button label text.
- **`set_button_visible(button_box, name, visible)`** — Shows or hides a button.
- **`set_connection(button_box, name, command)`** — Disconnects existing signal then connects a new slot.
- **`configure_button(button_box, name, conf)`** — Applies visibility and text from a config dict.
- **`_get_button(button_box, name)`** — Safely retrieves a `QAbstractButton` by `StandardButton` name.
- **`format_elapsed_time(elapsed, info)`** — Formats seconds into `"Time Elapsed: Xm Ys (info)"`.

#### `display/popup.py`
A flexible `QMessageBox` wrapper for consistently styled popup dialogs.

- **`show(title, text, icon, buttons, ...)`** — Core function. Applies the current theme via `themes.apply()` before showing.
- **`show_error(title, message, details)`** — Critical icon, acknowledge button.
- **`show_warning(title, message, details)`** — Warning icon, acknowledge button.
- **`show_info(title, message, details)`** — Information icon, acknowledge button.
- **`show_question(title, message, details, cancel_button)`** — Question icon, Yes/No (optional Cancel). Returns `True` if user clicked Yes.

---

### UI
Contains the static UI definitions.

#### `ui/interface.py`
Defines the `UiDialog` class, which constructs the graphical elements of the window.

- **Layout**: Manages the geometry and positioning of labels, buttons, and progress bars.
- **Backdrop**: Sets up the background image and filler widgets for Windows-native styling.
- **Translations**: Handles text setting via `retranslate_ui`.

---

### Library (`src/atlas/lib`)
Core utilities for application state, configuration, and OS integration.

#### `lib/browsers.py`
Manages browser configuration loading and validation.

- **`verify_entries(browsers_json, types_json)`** — Loads and validates `browsers.json`. Populates the global `BROWSERS` dict and `_PATH_CACHE`. Returns `False` if invalid or empty. Accepts optional injected data for testing.
- **`grab()`** — Returns a read-only `MappingProxyType` view of the cached `BROWSERS` dict.
- **`_validate_entry(entry, browser, system)`** — Validates a single browser path entry against `_REQUIRED_FIELDS`.

#### `lib/read.py`
Safely loads JSON configuration files.

- **`load_json(filename, config_dir)`** — Resolves the correct path for both dev and PyInstaller (frozen) builds. Navigates from `src/atlas/lib/` up three levels to the project root, then into `configs/`. Returns an empty dict on failure.

#### `lib/themes.py`
Cross-platform theming and resource loading.

- **`initialize(window)`** — Full theme setup entry point: sets window icon, applies backdrop, calls `apply()`, and (Windows-only) connects `colorSchemeChanged` for live theme switching.
- **`apply(window)`** — Detects the current theme via `_get_theme()` and dispatches to `_apply_light()` or `_apply_dark()`. Used by both `initialize()` and `popup.show()`.
- **`_get_theme()`** — Reads `AppsUseLightTheme` from the Windows Registry. Returns `"Light"` on non-Windows or on failure.
- **`_apply_light(window)`** — Applies a minimal light stylesheet (Windows-only).
- **`_apply_dark(window)`** — Applies a full dark stylesheet using `dwmapi.DwmSetWindowAttribute` for title bar theming. Applies rounded button styles on Windows 11+.
- **`_is_windows_11_or_newer()`** — Checks build number (`>= 22000`) for Windows 11 detection.
- **`resource_path(filename)`** — Resolves a path under `assets/` for both dev and frozen builds.
- **`backdrop(element)`** — Loads `images/Backdrop.png` and sets it as a scaled `QPixmap` on the given label.
- **`icon(window)`** — Loads `icons/Icon.ico` and sets it as the window icon.

#### `lib/directories.py`
Cross-platform user directory resolution.

- **`get_downloads_dir()`** — Resolves the current user's Downloads directory. Uses `SHGetKnownFolderPath` and registry lookup on Windows; `xdg-user-dirs` and ENV vars on Linux/BSD. Creates the directory if missing, and falls back to an executable-adjacent `output/` folder as a guaranteed last resort.

#### `lib/integration.py`
User-facing operating system integration helpers.

- **`open_folder(folder_path)`** — Resolves and opens a directory in the system file manager. Falls back to `archive.get_zip_output_dir()` if no path is given. Shows a `show_warning()` popup on failure.
- **`_open_folder_platform(folder_path)`** — Platform dispatch: `os.startfile` on Windows, `open` on macOS, `xdg-open` (via `subprocess.Popen` with a clean environment) on Linux.

#### `lib/permissions.py`
Ensures the application runs without elevated privileges.

- **`is_elevated()`** — Checks `os.geteuid() == 0` on Unix-like systems, `IsUserAnAdmin()` on Windows. Returns `False` safely on error.
- **`show_elevated_permissions_dialog()`** — Calls `show_warning()` and exits with code `1`. Falls back to console logging if the display module is unavailable.

---

### Backup
Contains the business logic for backup operations.

#### Low-Level Backup Flow

```text
User Action
  → Worker Thread Spawned
  → Profile Discovery (scan_profiles)
  → Size Estimation (estimate_size)
  → Disk Space Validation (check_disk_space)
  → Archive Creation (perform_backup → compress)
  → Progress Updates
  → Completion / Error Signal
```

All backup logic executes outside the main UI thread.

---

#### `backup/worker.py`
Defines `Worker(QObject)` — the PyQt bridge between the pipeline and the UI.

**Signals emitted:**

| Signal | Payload | Description |
|--------|---------|-------------|
| `progress` | `int, int` | Archive completion progress |
| `done` | — | Pipeline finished (success or cancelled) |
| `estimated_size` | `str` | Formatted estimated size string |
| `scanned_entries` | `str` | Scan status text |
| `disk_space_error` | `str, str` | Required and available space |
| `no_browsers_found` | — | No profiles found |
| `cancelled` | — | Worker was cancelled |

**`run()`** — Delegates the entire execution to `pipeline.run()`.

**`cancel()`** — Calls `pipeline.cancel()` and emits `cancelled`.

#### `backup/pipeline.py`
Defines `Pipeline` — the UI-agnostic backup orchestrator. Resolves policy directly internally.

- **`__init__(no_browsers_found_callback, disk_space_error_callback, estimated_callback, scanned_callback, progress_callback)`** — Accepts optional callbacks for UI reporting. Loads browser data via `browsers.grab()`.
- **`run()`** — Executes the full backup flow: `scan_profiles()` → `estimate_size()` → `check_disk_space()` → `perform_backup()`. Emits `no_browsers_found_callback` if scan returns nothing; emits `disk_space_error_callback` if space is insufficient.
- **`scan_profiles()`** — Iterates over all browsers, calls `Profile.find_profile(browser, os_name, browsers_data)` for each. Rate-limits status callbacks using `SIGNAL_BATCH_INTERVAL` (0.5s). Returns `Dict[str, List[str]]`.
- **`estimate_size(browser_matches)`** — Flattens unique profile paths, calls `Size.get_directory_size()` for each, accumulates total bytes. Emits formatted string via `estimated_callback`.
- **`perform_backup(browser_matches)`** — Creates a ZIP per browser via `archive.compress()`. Manually triggers `gc.collect()` after each archive to free memory. Emits `progress_callback` after each.
- **`cancel()`** / **`is_cancelled()`** — Cooperative cancellation flag checked at each pipeline stage.
- **`_retry_operation(operation, *args, **kwargs)`** — Retries up to `MAX_RETRIES` (3) times with exponential backoff (`RETRY_DELAY * 2^attempt`). Does not retry `PermissionError` or `FileNotFoundError`.

#### `backup/archive.py`
Handles ZIP archive creation.

- **`compress(source, zip_name, cancel_callback)`** — Main public API. Accepts a single path, a list of paths, or a mix. Calls `scan_files()` to gather valid files, then `write_zip()`. Cleans up the temp file on failure or cancellation.
- **`write_zip(files, sources, zip_path, cancel_callback)`** — Writes files to a `.zip.tmp` temp file, then atomically renames it to the final path via `os.replace()`. Validates the archive is non-empty before rename.
- **`_write_file_to_zip(zip_file, file_path, zip_info, cancel_callback)`** — Streams file content in `CHUNK_SIZE` (64 KB) chunks, checking cancellation each iteration.
- **`get_zip_output_dir()`** — Returns the resolved Downloads directory containing the `Atlas` subfolder (via `directories.get_downloads_dir()`), ensuring write targets are organized cleanly in the user's space.
- **`generate_zip_name()`** — Generates a timestamped fallback filename (`Unknown_YYYYMMDD_HHMMSS_ffffff.zip`).

#### `backup/filter.py`
File scanning and blacklist filtering.

- **`scan_files(source_paths, cancel_callback)`** — Walks each source directory, pruning blacklisted folders in-place. Skips symlinks, files with blacklisted extensions, Windows alternate data streams (`:` in filename), and files over `MAX_FILE_SIZE` (25 GB). Returns `List[Path]`.
- Blacklist data loaded at module import from `blacklist.json` via `load_json()`: `SKIP_FOLDERS`, `SKIP_FILE_EXTENSION`, `SKIP_FILE_WITH_EXTENSION`.

#### `backup/attribute.py`
ZIP entry metadata management.

- **`create_zip_info(file_path)`** — Creates a `zipfile.ZipInfo` with a safe timestamp and platform-appropriate permissions.
- **`safe_zipinfo_date(file_path)`** — Clamps file mtime to the ZIP-legal range (1980–2107).
- **`set_file_permissions(st_mode)`** — Returns `external_attr` for the ZipInfo. On Windows XP/Vista (major < 6 or minor ≤ 1), uses a fixed `0o600` permission to avoid legacy issues; otherwise uses the actual `st_mode`.
- **`get_windows_version()`** — Returns `(major, minor)` from `sys.getwindowsversion()` on Windows, else `None`.

#### `backup/disk.py`
Filesystem helpers for archive operations.

- **`safe_unlink(path)`** — Deletes a file, suppressing all errors. Used for temp file cleanup on failure.
- **`find_base_path(file_path, sources)`** — Finds which source directory contains a given file by checking `file_path.parents`.
- **`relative_zip_path(file_path, base_path)`** — Computes a sanitized relative path string for ZIP entries. Normalizes separators to `/` and strips NUL bytes.

#### `backup/profile.py`
Browser profile detection.

- **`find_profile(browser_name, operating_system, browsers_data)`** — Locates all valid profile directories for a browser on the current OS. Expands paths using `_expand_path_by_type()` and validates them with `_validate_profile_path()`. Deduplicates by normalized lowercase path.
- **`get_browser_name_from_path(path_str, browsers_data)`** — Reverse-lookup: given a profile path, returns the matching browser name or `"Unknown"`.
- **`_expand_path_by_type(path_type, path)`** — Looks up base paths for the type from `types.json`, expands env vars, resolves wildcards via `_expand_wildcard()`, and deduplicates.
- **`_expand_wildcard(base, rel_path)`** — Recursively resolves wildcard segments (`*`, `?`) in paths using `fnmatch`. Handles both literal and glob segments.
- **`_validate_profile_path(path, signature)`** — Checks that the path exists and contains the required signature file(s). Results are cached in `_PATH_CACHE` keyed by `(lower_path, signature)`.

#### `backup/size.py`
Size calculation and disk space utilities.

- **`get_directory_size(path_str)`** — Recursively sums file sizes, skipping blacklisted folders and symlinks. Calls `gc.collect()` every `CHUNK_SIZE` (1000) files. Enforces a `MAX_SCAN_TIME` (300s) timeout.
- **`format_size(bytes_size)`** — Converts bytes to a human-readable string (B, KB, MB, GB, TB, PB). Strips trailing zeros where appropriate.
- **`check_disk_space(estimated_size_bytes, output_path)`** — Checks if the output drive has at least `estimated_size * 1.5` bytes free. Returns `(bool, formatted_available_str)`.
- **`create_output_dir(output_path)`** — Creates the output directory, raising on failure.
