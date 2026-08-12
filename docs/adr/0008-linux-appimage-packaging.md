# 8. Linux AppImage Packaging

Date: 2026-08-09

## Context

Atlas needs a Linux release that can run across supported desktop systems
without extracting a PyInstaller one-file executable into a temporary
directory at each launch. Creating an AppImage additionally requires a
standard AppDir launcher, desktop entry, icon, and `appimagetool`.

`appimagetool` is distributed by its maintainers as a downloadable AppImage,
not as a package in the standard Ubuntu repositories. Downloading executable
tools should always remain a user-controlled action.

## Decision

Use `appimage.spec` to produce a PyInstaller onedir payload at
`dist/Atlas.AppDir/usr/bin`. Keep AppImage metadata in
`installer/appimage/`, and assemble the final AppDir with
`scripts/build_appimage.sh`.

Use `assets/icons/Icon.svg` as the Linux icon source of truth. Use that SVG
for the Linux application window and install it as the AppDir root icon.
Windows keeps its separate native icon asset.

The build script reuses an installed `appimagetool` when available. Otherwise
it asks before downloading the official tool to `~/.local/bin`. If the user
declines, or the download fails, the script still completes the PyInstaller
build and leaves the AppDir ready for manual packaging.

## Consequences

- Atlas does not use PyInstaller's one-file extraction for AppImage releases.
- The project root remains free of AppImage metadata files.
- AppImage desktop integration and the Linux application window use the same
  SVG asset; Windows retains its separate native icon asset.
- Producing the final `.AppImage` requires an existing or user-approved
  `appimagetool`; preparing an AppDir does not.
- The packaging tool uses extract-and-run mode so FUSE is not needed on the
  build machine merely to run `appimagetool`.
