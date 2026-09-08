# 10. FreeBSD Package Distribution

Date: 2026-09-07

## Status

Accepted

## Context

Following the implementation of Linux AppImage and Debian package deployment, we needed to properly support FreeBSD (and FreeBSD-derivatives like GhostBSD). 
While PyInstaller natively targets FreeBSD during build time, deploying the resulting standalone directories is a poor experience due to non-standard desktop integration and manual path management.

FreeBSD has a robust native package manager (`pkg`) that utilizes `.pkg` archives containing properly mapped binary files, library assets, and desktop application configurations (`+MANIFEST`, `plist`).

## Decision

We will automate the creation of native FreeBSD `.pkg` installers via a dedicated script (`scripts/build_pkg.sh`).

1. **Reuse Existing PyInstaller Payloads**: To ensure consistency across Unix-like systems and keep build times down, we utilize the exact same `onedir` payload built during the PyInstaller Linux/BSD freezing step.
2. **Native Tooling**: We use FreeBSD's native `pkg create` utility instead of relying on third-party packaging abstraction layers (e.g., FPM). 
3. **Dynamic Packing List (`plist`)**: `pkg create` requires an explicit file manifest. Since PyInstaller's outputs frequently shift based on Python dependencies, `build_pkg.sh` dynamically generates the `plist` by scanning the temporary packaging directory, preventing "Missing File" packaging faults while rejecting extraneous metadata like the `+MANIFEST` itself.
4. **Standardized XDG Desktop Integration**: The build script embeds XDG-compliant absolute paths into the `/usr/local/share/applications/atlas.desktop` configuration and writes the icon SVG into `/usr/local/share/icons/hicolor/scalable/apps/`. This enforces compatibility with FreeBSD-centric desktop environments like MATE and bypasses system icon themes that might intercept ambiguous generic names (e.g., "atlas").

## Consequences

- **Positive:** Users on FreeBSD and GhostBSD receive a first-class installation experience compatible with `sudo pkg add`. Desktop environments correctly cache and render the application menu shortcut.
- **Positive:** Development and build workflows seamlessly span Linux and FreeBSD with isolated, standard bash scripts (`build_appimage.sh`, `build_deb.sh`, `build_pkg.sh`).
- **Negative:** Supporting FreeBSD demands that the packaging logic correctly sets the installation prefix (to `/`) rather than `/usr/local`, offsetting the internal `usr/local/...` structure, introducing a slight deviation from traditional FreeBSD port behaviors. However, the end-user outcome is identical.
