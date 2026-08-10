<div align="center">
  <img src="assets/icons/Icon.svg" alt="Atlas icon" width="104" height="104">
  <h1>Atlas</h1>
  <p><strong>Reliable, offline browser-profile backups.</strong></p>
  <p>
    <a href="https://github.com/JunimoByte/atlas/actions/workflows/ci.yml">
      <img src="https://github.com/JunimoByte/atlas/actions/workflows/ci.yml/badge.svg?branch=main" alt="CI status">
    </a>
    <a href="https://www.python.org/">
      <img src="https://img.shields.io/badge/python-3.8%2B-3776AB?logo=python&amp;logoColor=white" alt="Python 3.8 or later">
    </a>
    <a href="LICENSE">
      <img src="https://img.shields.io/badge/license-AGPL--3.0--or--later-blue.svg" alt="License: AGPL-3.0-or-later">
    </a>
  </p>
</div>

## Information

Atlas creates portable ZIP backups of browser profiles while keeping the source data read-only.

## Features

- Supports 250+ Chromium, Gecko, and legacy browser variants, including Dev, Beta, and Nightly channels.
- Excludes caches and temporary data, often reducing a 1 GB+ profile to about 100 MB while preserving settings, history, and bookmarks.
- Uses a strictly read-only source model and atomically creates ZIP archives in a user-selected location.
- Supports Windows 7 through 11, Linux (glibc 2.31+), a Windows portable executable, Linux AppImage, and Python-package installs.

## Requirements

- Python 3.8+
- PyQt6 6.0+ (PyQt5 is the fallback for older Windows/Python)
- Linux builds: glibc 2.31+; Ubuntu 20.04 LTS is the preferred baseline

For Linux builds, first run:

```bash
source scripts/setup_dev.sh
```

The setup script checks XCB/XWayland libraries for reliable Qt startup and asks before installing missing dependencies.

## Install and run

```bash
pip install .
atlas
```

For development:

```bash
pip install -e ".[dev]"
python -m atlas.main
```

## Test

```bash
pytest
```

For headless Linux or CI execution:

```bash
QT_QPA_PLATFORM=offscreen pytest
```

## Build

### Windows portable executable

```bash
pyinstaller main.spec
```

The output is `dist/Atlas-x86_64-Portable.exe` for a 64-bit Python build or
`dist/Atlas-x86-Portable.exe` for a 32-bit build. The Inno Setup installer
uses the matching file automatically and installs it without `-Portable`.

### Linux AppImage

```bash
bash scripts/build_appimage.sh
```

This creates `dist/Atlas-<architecture>.AppImage` from an onedir payload, avoiding PyInstaller one-file extraction at launch. If `appimagetool` is absent, the script asks before downloading it to `~/.local/bin`; declining or a failed download still leaves a ready-to-package AppDir at `dist/Atlas.AppDir`.

Linux uses `assets/icons/Icon.svg` for the application and AppImage icon.

## Structure

| Location | Purpose |
| --- | --- |
| `src/atlas/` | Application code and tests |
| `configs/` | Browser definitions and backup policy |
| `assets/` | Application images and icons |
| `scripts/` | Setup and build scripts |
| `installer/` | Platform packaging metadata |

## License

GNU Affero General Public License v3.0 or later. See [LICENSE](LICENSE).
