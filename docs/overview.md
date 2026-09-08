# Overview

Atlas is a comprehensive, cross-platform utility designed to safeguard your web browsing data. It provides a simple yet powerful way to back up profiles from a vast array of web browsers.

## Features
Atlas supports over **250** different browser variants. It detects and backs up not just standard releases, but also:
*   **Development Builds** (Dev, Beta, Nightly)
*   **Canary Channels**
*   **Legacy Versions** & Older Engines

> **Disclaimer:** Due to Chromium's hardware-level encryption (DPAPI), logins must be manually exported/imported. All other data (Bookmarks, History, Settings) is fully backed up.

### 🖥️ Cross-Platform Compatibility
Engineered for maximum portability, Atlas runs on diverse operating systems:
*   **Windows**: 7 (see upcoming `win7` branch), 8, 10, 11.
*   **Linux (glibc 2.31+)**: Build portable releases on Ubuntu 20.04 LTS for
    the broadest practical compatibility with newer Linux desktop systems.
*   **FreeBSD/GhostBSD**: Native support with automated `.pkg` generation.

### Linux and BSD Desktop Compatibility

Atlas uses Qt's XWayland/XCB backend on Unix-like platforms, including in Wayland sessions.
This is intentional: it provides more consistent Qt theming, window
decorations, and behavior across the desktop environments commonly used from
Ubuntu 20.04 LTS onward, as well as on FreeBSD-based systems.

The Linux development setup checks for the required XCB libraries and asks
before installing missing dependencies. It stops if the compatibility layer is
unavailable, preventing a portable build that may not start on another system.

### 📦 Self-Contained Architecture
Atlas packages its Python application and Qt resources into a portable
executable. Linux build hosts must provide the XCB/XWayland libraries checked
by `scripts/setup_dev.sh`; this keeps release builds compatible with Atlas's
required desktop backend.

For Linux distribution, `scripts/build_appimage.sh` builds an AppImage-ready
onedir payload. It asks before downloading `appimagetool` when the tool is not
already available. If the download is declined or unavailable, the script
still prepares `dist/Atlas.AppDir` for manual packaging.

## Running Atlas

**From Source:**
```bash
python -m atlas.main
```

**As a Package:**
```bash
pip install .
atlas
```

## Project Structure

```
Atlas/
├── pyproject.toml         # Project metadata and dependencies
├── src/                   # Source code
│   └── atlas/             # Main package
│       ├── main.py        # Application entry point
│       ├── lib/           # Core utilities
│       │   ├── browsers.py
│       │   ├── directories.py
│       │   ├── integration.py
│       │   ├── permissions.py
│       │   ├── read.py
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
└── docs/                  # Documentation
```

