# Atlas Knowledge Base

## Purpose

Atlas is an offline desktop utility that discovers browser profiles and
creates ZIP backups. Its operational model is deliberately defensive:
browser profile directories are read only and archives are written only to a
user-controlled output location.

## Supported Environments

Atlas is intended to run on Linux (glibc 2.31+) and Windows 7 or later. The
supported runtime is Python 3.8 or newer. Qt is supplied by PyQt6 when
available, with PyQt5 selected as a fallback. Ubuntu 20.04 LTS is the
recommended Linux build baseline because it provides a broad compatibility
foundation for newer Linux desktop systems.

Linux configuration is performed before the Qt binding is imported. Atlas uses
XWayland/XCB for stable decorations and window flags, including on tiling
window managers. Users may explicitly select another backend with
`QT_QPA_PLATFORM`. Atlas does not load host-system Qt theme plugins into its
portable runtime, because their Qt ABI may not match the bundled Ubuntu 20.04
runtime. Frozen Linux builds also suppress incompatible system GIO modules and
the ATK bridge warning. The UI accommodates tiling window managers by using a
normal resizable window; on other desktops it uses a fixed-size dialog.

`scripts/setup_dev.sh` checks the XCB runtime libraries retained for X11
fallback compatibility. Atlas selects them unless the user chooses a different
backend with `QT_QPA_PLATFORM`.

## Startup and Application Flow

The executable entry point is `atlas.main`, also exposed as the `atlas`
console command. Startup follows this order:

1. Refuse elevated/admin execution.
2. Load and validate browser and path-type configuration.
3. Create `QApplication` and the main `Window`.
4. Initialize the window theme, application icon, and backdrop.
5. Enter the Qt event loop.

The backup operation follows a separate staged flow:

```text
Scan profiles -> estimate size -> validate free space -> create ZIP archives
```

The pipeline is cancelable and runs away from the main GUI thread.

## Qt Compatibility Boundary

`atlas.compatibility.qt` is the single Qt import boundary. Application code
imports `QtCore`, `QtGui`, and `QtWidgets` from this module rather than from a
specific PyQt package. The module resolves PyQt6 first, then PyQt5, and raises
an import error only when neither binding is installed.

This boundary also owns Linux environment setup that must occur before Qt is
loaded. UI code, dialogs, threads, timers, and signals use the exported Qt
names, keeping the rest of the application independent of the installed
binding.

## Interface and Window Model

`atlas.ui.interface.UiDialog` owns the static widget tree. It constructs:

- A title and backdrop.
- Four mutually exclusive status labels: initial description, progress,
  completion, and cancellation.
- An elapsed-time label and progress bar.
- A standard OK/Cancel dialog button box.

The layout has a nominal 407 x 290 minimum size and uses layout managers,
scaled fonts, word-wrapped labels, and Qt translation calls. The main
`atlas.display.window.Window` owns behavior rather than layout. It changes
the visible widgets and button actions through four modes:

| Mode | Visible content | Primary action | Secondary action |
| --- | --- | --- | --- |
| Idle | Introduction | Start scan | Close |
| Scanning | Progress and elapsed time | Hidden | Cancel |
| Completed | Completion text | Open output folder | Close |
| Error/cancelled | Cancellation text | Hidden | Close |

Buttons use a declarative configuration and are reconnected as the mode
changes. Linux button icons are removed for consistent rendering.

## Event and Background-Work Design

`display.signals.Signals` is the UI event contract. It carries backup start,
finish, cancellation, progress, estimated size, scan status, elapsed time,
disk-space errors, no-profile results, and worker failures.

`display.controller.Controller` owns the background-worker lifecycle and
tracks it with `IDLE`, `RUNNING`, `SUCCESS`, `EMPTY`, `BLOCKED`,
`CANCELLING`, and `FAILED` states. It deploys `backup.worker.Worker` in a
`QThread`, forwards its events through `Signals`, and updates elapsed time
every 300 milliseconds. Cancellation requests cooperative pipeline shutdown,
then waits for thread completion and cleans up the worker.

`backup.worker.Worker` is only a Qt adapter. The backup workflow itself is
implemented in the Qt-free `backup.pipeline.Pipeline`, which can be used from
tests and headless code through `backup.runner.run_pipeline`.

## Backup Data Flow

Browser definitions come from `configs/browsers.json`; path expansion types
come from `configs/types.json`. `lib.browsers.verify_entries` validates and
caches these files during startup, then exposes a read-only mapping.

OS keys in these configuration files (`Windows`, `Linux`, `Macos`, `BSD`) are
agnostic. They are mapped dynamically via `lib.system.normalize_os_key` to match
the current platform (`platform.system()`), ensuring variants like GhostBSD or
OpenBSD resolve correctly to `BSD`.

For each configured browser, `Pipeline.scan_profiles` resolves candidate
locations for the current operating system and verifies profile signatures.
It reports scan status in batches. Found profile directories are deduplicated
before size estimation. The pipeline then checks free space at the output
location and creates one archive per browser, reporting archive progress.

Archive creation streams files into a temporary ZIP, validates it, and uses
an atomic replace to publish the finished archive. Filtering excludes unsafe
or nonessential content such as paths outside the selected profile set,
symlinks, system files, blacklisted paths, unreadable files, very large
files, and Windows alternate data streams. Cancellation is checked throughout
the scan and write process.

## Filesystem and OS Integration

The normal archive destination is an `Atlas` directory under Downloads.
Downloads resolution is platform specific:

- Windows: known-folder API, registry, user Downloads directory, then an
  executable-adjacent fallback.
- Linux/BSD: XDG user directory configuration, `XDG_DOWNLOAD_DIR`, user
  Downloads directory, then an executable-adjacent fallback.
- macOS: user Downloads directory.

After success, the interface can open the output directory using the native
file manager (`os.startfile` on Windows and `xdg-open` on Linux). The program
does not require network access, telemetry, or elevated permissions.

## Themes and Packaged Resources

`lib.themes` loads the icon and backdrop from `assets/` and resolves their
paths for both source and PyInstaller builds. Windows receives registry-based
light/dark styling, DWM title-bar styling where available, and live theme
updates on supported Qt versions. Other platforms use Qt-provided theme
information with safe fallbacks.

`main.spec` creates the Windows-style portable executable. `appimage.spec`
creates a Linux onedir payload in `dist/Atlas.AppDir/usr/bin`, keeping the
application out of a PyInstaller one-file extraction step. The AppImage
launcher and desktop metadata are kept under `installer/appimage/`, and
`scripts/build_appimage.sh` assembles them into the AppDir. The script asks
before downloading a missing `appimagetool`; a declined or failed download
still leaves the AppDir ready for manual packaging. Both specs omit web
engines, network-capable Qt modules, and unrelated frameworks to preserve the
offline-first runtime.

`scripts/build_deb.sh` reuses that same Linux onedir payload to create a
native Debian package. The packaged application remains isolated in
`/opt/atlas`; the package adds only a launcher in `/usr/bin`, a desktop entry,
and license metadata. It requires the standard `dpkg-deb` tool but does not
install build or runtime dependencies system-wide. The Debian desktop entry
uses the bundled SVG icon directly rather than adding a separate icon-theme
asset tree.

Both PyInstaller specs enforce the offline packaging policy for PyQt5 and
PyQt6 equally. They explicitly exclude Qt networking, web-engine, WebSocket,
Bluetooth, remote-object, and related standard-library networking modules.
After analysis, each spec rejects a build if its collected payload includes a
blocked module or optional Qt feature binary. Qt itself may
carry the shared QtNetwork runtime library transitively; the check instead
verifies that Atlas does not ship its Python network API or optional network
features. It is not a replacement for an operating-system firewall.

GitHub Actions builds the Linux payload and runs the test container with
Docker networking disabled. A startup test also replaces Python socket
creation, DNS resolution, and connection helpers with failures, then exercises
Atlas's normal startup path. Together, these checks fail CI if the package
collects a blocked component, the application tries to use Python network APIs
at startup, or the tested runtime requires network connectivity.

The Windows spec names releases from the Python interpreter bitness:
`Atlas-x86_64-Portable.exe` for 64-bit Python and
`Atlas-x86-Portable.exe` for 32-bit Python. `installer/Atlas.iss` detects the
available portable build and installs it as the corresponding
`Atlas-<architecture>.exe`.

The Debian build uses the matching release-artifact convention, such as
`Atlas-x86_64.deb`. Its internal Debian package metadata still uses the
required Debian architecture identifiers, such as `amd64`.

`assets/icons/Icon.svg` is the Linux icon source. The application window and
AppImage root both use that SVG directly. Windows uses its native icon asset
separately.

## Code Map

| Location | Responsibility |
| --- | --- |
| `src/atlas/main.py` | Startup checks and Qt application launch. |
| `src/atlas/compatibility/qt.py` | Qt binding selection and Linux pre-Qt setup. |
| `src/atlas/ui/interface.py` | Static main-dialog widgets and layout. |
| `src/atlas/display/` | Window modes, controller, signals, controls, dialogs. |
| `src/atlas/backup/` | Discovery, sizing, validation, filtering, and archiving. |
| `src/atlas/lib/` | Configuration, themes, permissions, folders, OS integration. |
| `configs/` | Browser locations, path types, and blacklist policy. |
| `main.spec` | PyInstaller packaging definition. |
| `appimage.spec` | Linux onedir payload definition for AppImage builds. |
| `installer/appimage/` | AppImage launcher and desktop entry. |
| `scripts/build_appimage.sh` | Consent-based AppDir and AppImage build script. |
| `installer/debian/` | Debian package control, launcher, and desktop metadata. |
| `scripts/build_deb.sh` | Debian package build script using the Linux onedir payload. |

## Testing and Headless Use

Unit tests are located in `src/atlas/tests/unit`; integration tests are in
`src/atlas/tests/integration`. GUI tests can run without a desktop by setting
`QT_QPA_PLATFORM=offscreen`. The repository's standard unit-test command is:

```powershell
.\venv\Scripts\python.exe -m pytest src/atlas/tests/unit --tb=short -q
```
