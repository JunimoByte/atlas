# Runtime Contracts

This document records the small set of runtime rules that affect every Atlas
platform. Read it before changing packaging metadata, filesystem scans, or Qt
threading.

## Configuration Resources

Always load configuration through `atlas.lib.read.load_json`; callers must not
derive a path to `configs/` themselves.

| Runtime | Configuration base |
| --- | --- |
| Source checkout | Repository `configs/` directory |
| Wheel, `pip --target`, `pip --prefix`, or `pip --user` | Installed `share/atlas/configs` directory, located relative to the package first |
| PyInstaller | `sys._MEIPASS/configs` |
| Flatpak fallback | `/app/configs` |

`pyproject.toml` lists the JSON files as setuptools data files and
`MANIFEST.in` includes them in source distributions. Update both locations
when adding a required configuration file.

## Qt Installation Policy

| Host | Binding supplied by `pip install .` |
| --- | --- |
| Python 3.8 on Windows, Linux, or macOS | PyQt5 |
| Python 3.9+ on Windows | PyQt6 |
| Python 3.9+ on Linux | PyQt6 below 6.8 for the glibc 2.31 baseline |
| Python 3.9+ on macOS | PyQt6 below 6.7.1 for legacy macOS compatibility |
| BSD and Solaris / Illumos | Native PyQt package, exposed with a `--system-site-packages` virtual environment |

`pyproject.toml` must not compare `platform_release` with a version operator.
PEP 508 evaluates marker terms on hosts where the platform does not match, and
Linux kernel releases such as `6.17.0-1022-azure` are not PEP 440 versions.
Use `platform_system` markers for package metadata. `scripts/setup_dev.sh` may
inspect native OS version commands when it needs more specific guidance.

## Backup and Filesystem Rules

- Profile discovery does not cache wildcard expansion or profile validation.
  A profile created, removed, or locked between scans must be observed on the
  next scan.
- A cancellation request, a size-scan timeout, or an unexpected filesystem I/O
  error makes the estimate unreliable. The pipeline must block the disk-space
  check instead of proceeding with a partial total.
- Storage exhaustion includes POSIX `ENOSPC`, `EDQUOT` where available, and
  Windows errors 112 and 39. It produces an insufficient-space result; it
  cannot produce successful archive progress.
- Archive and scan cancellation is cooperative. Check for it before expensive
  operations and while iterating files or directory entries.

## Qt Thread Ownership

- `backup.pipeline.Pipeline` is Qt-free and may run in headless code.
- Widgets and dialogs run only on the QApplication thread. A daemon thread
  reports a folder-opening failure through the queued warning dispatcher.
- `Controller.cancel_backup()` requests cancellation without blocking the UI.
  `Controller.cleanup()` returns success only after the worker has stopped.
  If it times out, `Window.closeEvent()` keeps the window alive; it must never
  destroy a running `QThread`.

## Maintainer Checks

Run these after changing a contract above:

```bash
pip install -e ".[dev]"
pytest
ruff check src
```

The packaging-metadata test also evaluates the dependency markers using a
non-PEP-440 Linux kernel release. It protects the Python 3.8 Linux CI install
step from marker regressions.
