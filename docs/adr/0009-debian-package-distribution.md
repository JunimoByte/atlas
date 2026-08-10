# 9. Debian Package Distribution

Date: 2026-08-10

## Context

AppImage is Atlas's portable Linux distribution, but Debian and Ubuntu users
also expect a package that integrates with the system package manager and can
be removed cleanly. Creating a second PyInstaller configuration would risk
the two Linux releases diverging.

## Decision

Reuse `appimage.spec` as the single Linux onedir payload. Use
`scripts/build_deb.sh` to stage that payload in `/opt/atlas`, add a minimal
`/usr/bin/atlas` launcher and desktop entry, then build the package with
`dpkg-deb`.

Keep Debian metadata under `installer/debian/`. The desktop entry uses the
SVG stored inside the payload by absolute path, avoiding a second icon asset
or icon-theme directory tree.

## Consequences

- AppImage and Debian releases execute the same PyInstaller payload.
- Installing or removing the package affects only Atlas-owned files.
- `dpkg-deb` is required only on the build machine; Atlas has no system
  Python or Qt runtime dependency.
- Debian package filenames follow the conventional
  `atlas_<version>_<architecture>.deb` format.
- The package should be built on the oldest supported Linux baseline to
  retain the intended glibc compatibility.
