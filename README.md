# Atlas

Atlas is an application for backing up and moving browser profiles. It is designed for reliability, especially on legacy systems where cloud-based tools are unavailable.

Software moves fast and often leaves older hardware behind. Atlas was built to ensure your data stays yours, regardless of the machine you are using.

## Features

- **Wide Browser Support**: Supports over 250 browser variants across Chromium, Gecko, and legacy engines. Compatibility depends on the specific browser version and host OS.
- **Intelligent Snapshots**: Filters non-essential data like caches and temporary files, drastically reducing storage footprint (often from 1GB+ down to ~100MB) while preserving all critical history and settings.
- **High-Fidelity Preservation**: Engineered for extreme stability and data integrity, approaching forensic standards for read-only profile capture.
- **Legacy Compatibility**: Native support for Windows 7, 8, 10, and 11.
- **Deployment Flexibility**: Available as both a standalone portable executable and a standard installable Python package.
- **Safety**: Strict read-only model. Atlas does not modify source profile data or touch sensitive system directories.

## How it Works

Atlas follows a simple process for data reliability:

1. **Check**: Verifies permissions and the system environment.
2. **Scan**: Finds supported profiles automatically.
3. **Estimate**: Calculates sizes and checks if your destination has enough space.
4. **Backup**: Creates archives using safe, atomic operations.

## Development

### Requirements

- Python 3.8 or higher
- PyQt6 6.5 or higher

### Installation from Source

To install Atlas as a package from the source directory:

```bash
pip install .
```

For development with testing and build tools:

```bash
pip install -e ".[dev]"
```

### Running

The application can be launched directly:

```bash
python -m atlas.main
```

Or via the installed command:

```bash
atlas
```

### Testing

Tests are located in `src/atlas/tests`. Run them using pytest:

```bash
pytest
```

### Building

Atlas uses PyInstaller for creating standalone executables. Use the provided spec file:

```bash
pyinstaller main.spec
```

### Build Optimizations

The `main.spec` configuration explicitly excludes several modules to reduce the executable size and improve security. By removing network-capable libraries, Atlas ensures a lean, offline-first environment:

- **Network Modules**: `QtNetwork`, `http`, `ssl`, `ftplib`, `smtplib`, etc.
- **Web Engines**: `QtWebEngineWidgets`, `QtWebEngineCore`.
- **Unused Large Frameworks**: `QtQuick`, `Qt3D`, `QtMultimedia`, `tkinter`.

## Structure

| Directory | Purpose |
| :--- | :--- |
| `src/atlas/` | Main application package |
| `src/atlas/lib/` | Core utilities and OS integration |
| `src/atlas/backup/` | Profile discovery and archiving logic |
| `src/atlas/display/` | UI controllers and window management |
| `src/atlas/ui/` | Static UI layouts |
| `configs/` | Browser definitions and blacklists |
| `assets/` | Icons and images |

## Roadmap

- **Windows 7 Support**: Native performance and feature parity to be maintained under the upcoming `win7` branch.
- **Windows XP Support**: Support for legacy engines and XP-specific environments to be maintained under the upcoming `legacy-atlas` branch.
- **Linux**: Porting backup tools to the Linux platform.
- **Research**: Expanding the list of supported historical browser engines.

## Getting Started

Atlas is portable. No installation is required for end users.

1. Download the latest release.
2. Run `Atlas-Portable.exe`.

## License

**GNU Affero General Public License v3.0 (AGPL-3.0)**.
Copyright (c) 2026 Atlas.

---

<sub>*A personal note: I spent 8 months building this app, installing and exploring over 250 browser variants along the way. It was the most challenging project I've taken on, but seeing it come to life made it worth it.*</sub>