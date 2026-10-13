# 13. Unified Application Versioning & Single Source of Truth

Date: 2026-10-13

## Status

Accepted

## Context

Prior to this decision, application version strings were hardcoded across multiple disjointed files throughout the repository:
- `pyproject.toml` (`project.version`)
- `src/atlas/args.py` (cached fallback constant)
- `src/atlas/ui/interface.py` (HTML title label)
- `installer/Atlas.iss` (Inno Setup `#define MyAppVersion`)
- `src/atlas/tests/unit/test_args.py` and `test_main.py` (hardcoded assertion checks)
- Packaging metadata files across Linux and BSD distributions

This scattered state made cutting new releases error-prone:
1. Bumping the version required hunting down and editing several separate files.
2. Missed edits caused discrepancies where the binary reported one version via CLI, but the GUI title or installer reported an older version.
3. Unit tests broke on version bumps due to hardcoded string comparisons.

## Decision

We establish `pyproject.toml` as the **Single Source of Truth** for the application version and unify all application layers to derive their version dynamically from this single definition.

### 1. Core Python Runtime (`atlas.args`)
- `src/atlas/args.py` provides `get_version()`, which dynamically reads and caches the version from `pyproject.toml` (or `importlib.metadata` if installed as a package).
- A generic fallback (`"0.0.0"`) is maintained only for rare disconnected runtime environments, completely decoupling `args.py` from specific release numbers.
- Exposes `VERSION: str` globally for use across the application.

### 2. GUI Layer (`atlas.ui.interface`)
- `src/atlas/ui/interface.py` dynamically imports `VERSION` from `atlas.args` and renders it into the main dialog header label (`Atlas <VERSION>`), eliminating hardcoded HTML strings.

### 3. Packaging & Installers
- **Windows Inno Setup (`installer/Atlas.iss`)**: Uses the Inno Setup Preprocessor (ISPP) function `ExecAndGetFirstLine` to execute `atlas.args.VERSION` at compile-time, inheriting the version directly from `pyproject.toml`.
- **Debian Package (`scripts/build_deb.sh`)**: Automatically parses `pyproject.toml` and replaces `@VERSION@` tokens in `installer/debian/control`.
- **FreeBSD Package (`scripts/build_pkg.sh`)**: Dynamically reads `pyproject.toml` and writes the FreeBSD `+MANIFEST` at build time.
- **Flatpak & AppImage**: Build directly from the project directory and AppDir payload, automatically bundling `pyproject.toml`.

### 4. Test Suite Decoupling
- Unit tests (`test_args.py`, `test_main.py`) validate semantic version formatting via regex and dynamically assert against `pyproject.toml` rather than expecting hardcoded version strings.

## Release Procedure (Cheat Sheet)

When releasing a new version (`1.3`, `1.4`, etc.), developers only need to perform the following:

1. **Required — Update Version in `pyproject.toml`**:
   ```toml
   [project]
   version = "1.3"
   ```
2. **Policy / Store Metadata (If applicable)**:
   - [`SECURITY.md`](../../SECURITY.md): Update the supported versions table.
   - [`installer/msix/AppxManifest.xml`](../../installer/msix/AppxManifest.xml): Update `Version="1.3.0.0"` if publishing to the Microsoft Store.
3. **Create Git Release Tag**:
   ```bash
   git tag -a v1.3 -m "Release 1.3"
   git push origin v1.3
   ```

## Consequences

- **Single Edit**: Releasing a new version requires updating only `pyproject.toml` in code.
- **Consistency**: GUI, CLI (`--version`), installers (Windows `.exe`, Debian `.deb`, FreeBSD `.pkg`, Flatpak, AppImage), and tests stay in lockstep automatically.
- **Zero Test Churn**: Version bumps no longer cause brittle test failures in CI.
