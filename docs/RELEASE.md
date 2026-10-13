# Atlas Release Playbook

This document is the standard operational guide for Atlas maintainers to prepare, verify, and publish official application releases.

---

## 1. Release Philosophy & Single Source of Truth

Atlas adheres to **[ADR 0013: Unified Application Versioning](adr/0013-unified-application-versioning.md)**:

- **Single Source of Truth**: The project version is defined **once** in [`pyproject.toml`](../pyproject.toml) under `[project].version`.
- **Dynamic Propagation**: 
  - Application runtime, CLI, and dynamic GUI header resolve version via [`src/atlas/args.py`](../src/atlas/args.py).
  - Inno Setup installer ([`installer/Atlas.iss`](../installer/Atlas.iss)) queries the version dynamically from Python.
  - Linux packages (`deb`, `pkg`, `flatpak`) parse the version from `pyproject.toml`.
  - Maintainers **do not** need to edit version strings across HTML or installer templates.

---

## 2. Standard 3-Step Release Procedure

### Step 1: Bump Version in `pyproject.toml`
Edit `pyproject.toml` in the repository root:

```toml
[project]
name = "atlas"
version = "1.3"  # <-- Update here (e.g., 1.3, 1.4, 1.2.1)
```

Commit the version bump:
```bash
git add pyproject.toml
git commit -m "chore(release): bump version to 1.3"
git push origin alpha  # or target release branch
```

---

### Step 2: Run Pre-Flight Verification
Execute the automated pre-flight release check:

```bash
python scripts/verify_release.py
```

The script verifies 6 critical release contracts in ~2 seconds:
1. **Git Working Tree**: Confirms working directory is clean.
2. **Version Format & Synchronization**: Validates semantic versioning and cross-checks that `pyproject.toml` matches `atlas.args.VERSION`.
3. **JSON Config Integrity**: Confirms all files in `configs/` parse cleanly.
4. **Inno Setup Resolution**: Confirms `installer/Atlas.iss` resolves the new version.
5. **Linters**: Runs `ruff` and `flake8` (skips gracefully if not installed).
6. **Test Suite**: Runs the full `pytest` test suite (480+ unit tests).

**Expected output:**
```text
=== Atlas Pre-Flight Release Verification ===
Target repository: ...

  [OK] Working directory is clean
  [OK] Version format '1.3' is valid and unified
  [OK] All 3 JSON config files parse cleanly
  [OK] Atlas.iss resolves version '1.3' cleanly
  [OK] Ruff linting passed cleanly
  [OK] Flake8 linting passed cleanly
  [OK] Pytest suite passed (480 passed in 1.15s)

===================================================
[OK] All checks passed. Atlas v1.3 is ready to tag.
===================================================
```

> [!WARNING]
> If any check displays `[FAIL]`, do **not** proceed to tag. Resolve the reported issue first.
> To test pre-flight locally on a dirty working tree without failing, pass `--allow-dirty`.

---

### Step 3: Tag and Publish
Once all pre-flight checks pass, create and push the annotated Git tag:

```bash
git tag v1.3
git push origin v1.3
```

Pushing a `v*` tag automatically triggers the official release builds on GitHub Actions:
- **Build Linux Release**: Compiles `Atlas-x86_64.AppImage`, `Atlas-x86_64.deb`, and `Atlas-x86_64.flatpak`.
- **Build FreeBSD Release**: Compiles FreeBSD packages on FreeBSD 14.1 and 13.4 runners.

---

## 3. On-Demand Builds via GitHub Actions

Release workflows do **not** run on routine commits to keep developer CI fast (~55s). If you need to build packaging artifacts on demand without creating a Git tag:

1. Navigate to the repository's **Actions** tab on GitHub.
2. Select the desired workflow in the left sidebar:
   - **Build Linux Release** (AppImage, DEB, Flatpak)
   - **Build FreeBSD Release** (FreeBSD 14.1 & 13.4 packages)
   - **Build Solaris Release** (Solaris 11.4 package)
3. Click the **Run workflow** dropdown button on the right.
4. Select the target branch (e.g. `alpha`, `beta`, `main`) and click **Run workflow**.
5. Once complete, download the built packages from the workflow's **Artifacts** section.

---

## 4. Local Windows Installer Build

To build the Windows executable and installer locally:

1. Build portable PyInstaller executables:
   ```cmd
   pyinstaller main.spec
   ```
   Outputs will be placed in `dist/Atlas-x86_64-Portable.exe` (or `dist/Atlas-x86-Portable.exe`).

2. Compile the Inno Setup installer:
   ```cmd
   iscc installer\Atlas.iss
   ```
   Inno Setup automatically detects the executable in `dist/`, resolves the version from Python, and compiles `installer\Output\Atlas-x86_64-Setup.exe`.

---

## 5. Rollback / Deleting an Accidental Tag

If a release tag was pushed prematurely or with an error:

1. Delete the local tag:
   ```bash
   git tag -d v1.3
   ```
2. Delete the remote tag on GitHub:
   ```bash
   git push origin :refs/tags/v1.3
   ```
