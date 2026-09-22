<div align="center">
  <img src="assets/icons/Icon.svg" alt="Atlas icon" width="104" height="104">
  <h1>Atlas</h1>
  <p><strong>Reliable, offline browser-profile backups.</strong></p>
  <p>
    <a href="https://github.com/JunimoByte/atlas/actions/workflows/ci.yml">
      <img src="https://github.com/JunimoByte/atlas/actions/workflows/ci.yml/badge.svg?branch=main" alt="CI status">
    </a>
    <a href="https://www.python.org/">
      <img src="https://img.shields.io/badge/python-3.8%2B-3776AB?logo=python&amp;logoColor=white" alt="Python 3.8+">
    </a>
    <a href="LICENSE">
      <img src="https://img.shields.io/badge/license-AGPL--3.0--or--later-blue.svg" alt="License: AGPL-3.0-or-later">
    </a>
  </p>
</div>

Atlas creates portable, lightweight ZIP backups of browser profiles while
never writing to any browser directory.

## Features

- **300+ Supported Browsers:** Comprehensive auto-detection for Chromium,
  Gecko, and legacy engines (Firefox, Chrome, Brave, Zen, LibreWolf,
  Waterfox, Floorp, Vivaldi, Arc, and 290+ more).
- **Intelligent Cache Stripping:** Excludes caches and disposable data,
  often shrinking 1 GB+ profiles to ~100 MB while preserving bookmarks,
  history, extensions, and preferences.
- **Strictly Read-Only:** Live browser folders are opened exclusively in
  read-only mode and are never modified, written to, or altered.
- **Headless & Automation Ready:** Full graphical interface and headless
  CLI mode (`--cli`) with cron-safe logging.
- **Cross-Platform:** Native support for Windows (7 through 11), Linux
  (glibc 2.31+), and BSD (FreeBSD, GhostBSD).

## Privacy & Offline Guarantee

Atlas is engineered from the ground up to respect user privacy:

- **100% Offline:** Zero telemetry, analytics, crash reporting, or cloud sync.
- **Physical Network Exclusion:** Standalone binary builds physically exclude
  standard networking libraries (`socket`, `ssl`, `http`, `QtNetwork`).
- **No Credential Decryption:** Atlas never decrypts DPAPI credentials,
  master keys, or saved browser passwords.
- **Local Ownership:** All archives remain on your local storage under your
  complete control.

> [!NOTE]
> CI builds the Linux payload and executes the test suite in a
> network-disabled container. Any attempt by the application to initiate
> a network connection immediately fails the build.

For full details, see the [Privacy Policy](PRIVACY.md).

## Quickstart

### Prebuilt Binaries

Download native executables and packages from [Releases](../../releases):

- **Windows:** Standalone portable `.exe` or Inno Setup installer
- **Linux:** Standalone `.AppImage` or `.deb` package
- **FreeBSD:** Native `.pkg` package

### Install with pip

```bash
pip install .
atlas         # Launch GUI
atlas --cli   # Run headless backup (cron / scripts)
```

## How It Works

1. **Auto-Detection:** Atlas scans standard locations across your system
   to identify installed browsers and their active profiles.
2. **Selective Archiving:** Disposable caches, crash dumps, and temporary
   files are bypassed during archive creation.
3. **Atomic Packaging:** Profiles are packaged into standard, non-proprietary
   ZIP archives.
4. **Transparent Restoration:** Because backups use standard folder layouts,
   restoring a profile is as simple as unzipping the archive back into the
   browser profile folder.

## Development

Atlas dev environment setup requires `bash` or `zsh`:

```bash
source scripts/setup_dev.sh
```

### Running Tests

```bash
pytest

# Headless Linux or CI execution:
QT_QPA_PLATFORM=offscreen pytest
```

### Building Releases

| Target Platform | Command | Output Artifact |
| :--- | :--- | :--- |
| **Windows** | `pyinstaller main.spec` | `dist/*-Portable.exe` |
| **Linux AppImage** | `bash scripts/build_appimage.sh` | `dist/*.AppImage` |
| **Debian / Ubuntu** | `bash scripts/build_deb.sh` | `dist/*.deb` |
| **FreeBSD** | `bash scripts/build_pkg.sh` | `dist/*.pkg` |

*For advanced packaging options and platform notes, see the [docs](docs/).*

## Structure

| Location | Purpose |
| :--- | :--- |
| `src/atlas/` | Application code and unit tests |
| `configs/` | Browser profiles, rules, and blacklist |
| `assets/` | Application icons and graphics |
| `scripts/` | Environment setup and build scripts |
| `installer/` | Platform packaging metadata |
| `docs/` | Architecture and platform documentation |

## License

GNU Affero General Public License v3.0 or later. See [LICENSE](LICENSE).
