# Overview

Atlas is a comprehensive, cross-platform utility designed to safeguard your web browsing data. It provides a simple yet powerful way to back up profiles from a vast array of web browsers.

## Features
Atlas supports over **300+** different browser variants. It detects and backs up not just standard releases, but also:
*   **Development Builds** (Dev, Beta, Nightly)
*   **Canary Channels**
*   **Legacy Versions** & Older Engines
*   **Headless CLI Support**: Execute backups via scripts or cron jobs
    without GUI dependencies using `atlas --cli`.

> **Disclaimer:** Due to Chromium's hardware-level encryption (DPAPI), logins must be manually exported/imported. All other data (Bookmarks, History, Settings) is fully backed up.

### 🖥️ Cross-Platform Kernel & OS Compatibility
Engineered for maximum portability across Windows, Linux, and BSD kernels:
*   **Windows (NT Kernel)**: 7, 8, 10, 11.
*   **Linux (Linux Kernel / glibc 2.31+)**: Build portable releases on Ubuntu 20.04 LTS for
    the broadest practical compatibility with newer Linux desktop systems.
*   **BSD (FreeBSD/GhostBSD Kernels)**: Native support with automated `.pkg` generation (recommended to compile on FreeBSD 13+ or GhostBSD 22+).

### Linux and BSD Desktop Compatibility

Atlas uses Qt's XWayland/XCB backend on Unix-like platforms, including in Wayland sessions.
This is intentional: it provides more consistent Qt theming, window
decorations, and behavior across the desktop environments commonly used from
Ubuntu 20.04 LTS onward, as well as on FreeBSD-based systems.

The Linux development setup checks for the required XCB libraries and asks
before installing missing dependencies. It stops if the compatibility layer is
unavailable, preventing a portable build that may not start on another system.

### 📦 Multi-Platform Packaging Architecture
Atlas packages its Python application and Qt resources into self-contained
releases tailored for each supported operating system:
*   **Linux AppImage (`scripts/build_appimage.sh`)**: Builds an onedir payload
    staged at `dist/Atlas.AppDir/usr/bin` and packages it into a standalone
    AppImage using `appimagetool`.
*   **Debian/Ubuntu (`scripts/build_deb.sh`)**: Reuses the Linux onedir payload
    under `/opt/atlas` to create standard `.deb` packages with system desktop
    and icon integration.
*   **FreeBSD / GhostBSD (`scripts/build_pkg.sh` & `scripts/install_bsd.sh`)**:
    Generates native FreeBSD `.pkg` packages bound to `/usr/local/` and
    provides an automated standalone runner script for cross-ABI
    compatibility.
*   **Windows Portable & Installer (`main.spec`, Inno Setup, MSIX)**: Compiles
    standalone portable executables (`Atlas-x86_64-Portable.exe`), Inno Setup
    installers, and MSIX packages for Microsoft Store distribution.

## Running Atlas

**From Source:**
```bash
python -m atlas.main
python -m atlas.main --cli
python -m atlas.main --version
```

**As a Package:**
```bash
pip install .
atlas
atlas --cli
atlas --version
```

## Project Structure

```
Atlas/
├── pyproject.toml         # Project metadata and dependencies
├── src/                   # Source code
│   └── atlas/             # Main package
│       ├── main.py        # Bootstrapper router
│       ├── gui.py         # Graphical entry point
│       ├── cli.py         # Headless entry point
│       ├── args.py        # Command-line parser & version resolution
│       ├── lib/           # Core utilities
│       │   ├── browsers.py
│       │   ├── directories.py
│       │   ├── integration.py
│       │   ├── permissions.py
│       │   ├── read.py
│       │   ├── system.py
│       │   └── themes.py
│       ├── backup/        # Backup logic
│       │   ├── worker.py
│       │   ├── runner.py
│       │   ├── pipeline.py
│       │   ├── archive.py
│       │   ├── filter.py
│       │   ├── attribute.py
│       │   ├── disk.py
│       │   ├── profile.py
│       │   └── size.py
│       ├── display/       # UI components
│       │   ├── window.py
│       │   ├── controller.py
│       │   ├── signals.py
│       │   ├── controls.py
│       │   └── popup.py
│       ├── ui/            # UI layouts
│       │   └── interface.py
│       └── tests/         # Test suite
├── assets/                # Application resources
│   ├── icons/             # Application icons
│   └── images/            # UI images
├── configs/               # JSON configuration files
│   ├── browsers.json
│   ├── types.json
│   └── blacklist.json
├── installer/             # Packaging metadata
│   ├── appimage/          # AppImage launcher and desktop entry
│   ├── debian/            # Debian control and desktop entry
│   └── msix/              # Windows Store MSIX manifest and assets
├── scripts/               # Build and environment setup scripts
└── docs/                  # Architecture, ADRs, and guides
    └── adr/               # Architecture Decision Records
```

