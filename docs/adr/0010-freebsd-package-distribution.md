# 10. FreeBSD Package Distribution

Date: 2026-09-07

## Status

Accepted

## Context

Following the implementation of Linux AppImage and Debian package deployment, we needed to properly support FreeBSD (and FreeBSD-derivatives like GhostBSD). 
While PyInstaller natively targets FreeBSD during build time, deploying the resulting standalone directories is a poor experience due to non-standard desktop integration and manual path management.

FreeBSD has a robust native package manager (`pkg`) that utilizes `.pkg` archives containing properly mapped binary files, library assets, and desktop application configurations (`+MANIFEST`, `plist`).

## Decision

We support two distribution methods for FreeBSD:

### 1. Native FreeBSD Packages (.pkg)
We automate the creation of native FreeBSD `.pkg` installers via a dedicated script (`scripts/build_pkg.sh`).

1. **Reuse Existing PyInstaller Payloads**: To ensure consistency across Unix-like systems and keep build times down, we utilize the exact same `onedir` payload built during the PyInstaller Linux/BSD freezing step.
2. **Native Tooling**: We use FreeBSD's native `pkg create` utility.
3. **Dynamic Packing List (`plist`)**: `pkg create` requires an explicit file manifest. `build_pkg.sh` dynamically generates this `plist`.
4. **Standardized XDG Desktop Integration**: The build script embeds XDG-compliant absolute paths into the desktop configuration.

### 2. Standalone Portable Executable (install_bsd.sh)
Because `.pkg` files enforce strict ABI architecture checks (e.g., FreeBSD 13 vs 14), distributing a pre-compiled `.pkg` file directly to users often fails. To bypass this, we distribute the standalone PyInstaller binary (`Atlas-x86_64-Portable`) alongside `install_bsd.sh`. This script installs the necessary compatibility packages (like `compat13x-amd64`) and mimics the `.pkg` desktop integration by moving the binary to `/usr/local/bin`.

## Consequences

- **Positive:** Users on FreeBSD and GhostBSD receive a first-class installation experience compatible with `sudo pkg add`. Desktop environments correctly cache and render the application menu shortcut.
- **Positive:** Development and build workflows seamlessly span Linux and FreeBSD with isolated, standard bash scripts (`build_appimage.sh`, `build_deb.sh`, `build_pkg.sh`).
- **Negative:** Supporting FreeBSD demands that the packaging logic correctly sets the installation prefix (to `/`) rather than `/usr/local`, offsetting the internal `usr/local/...` structure, introducing a slight deviation from traditional FreeBSD port behaviors. However, the end-user outcome is identical.
