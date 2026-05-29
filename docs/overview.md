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
*   **Windows XP**: See upcoming `legacy-atlas` branch for XP and older engine support.
*   **Linux**: GLIBC 2.23 and newer.

### 📦 Self-Contained Architecture
Atlas is a self-contained application, requiring no external dependencies. It includes all necessary components within a single executable, ensuring ease of use and portability.

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

