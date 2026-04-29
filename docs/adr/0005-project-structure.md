# 5. Project Structure: src/atlas Layout
Date: 2026-02-18
Last updated: 2026-03-16

## Context
Early development had modules at the root level (`backup/`, `display/`,
`ui/`) with a simple `main.py` launcher. This mixed source code with
configuration files and assets and made the project non-installable as a
proper Python package.

## Decision
All source code is organised under `src/atlas/`, following the standard
`src`-layout recommended by the Python Packaging Authority:

```
src/
  atlas/
    backup/       # scanning, estimation, and backup pipeline
    display/      # window, controller, and signal management
    lib/          # shared utilities (themes, integration helpers)
    tests/        # unit test suite (mirrors package structure)
    ui/           # Qt UI definitions
    main.py       # application entry point
assets/           # icons and images
configs/          # runtime configuration files
docs/             # documentation and ADRs
scripts/          # developer setup scripts
pyproject.toml    # build and dependency metadata
```

The application is launched via the `atlas.main` module, either through
the installed console script defined in `pyproject.toml` or a PyInstaller
bundle. There is no root-level `run.py` launcher.

## Rationale
- **Installability**: The `src/atlas` layout is the packaging standard;
  `pip install .` works without additional path manipulation.
- **Clean Root**: The project root contains only metadata files
  (`pyproject.toml`, `README.md`, `LICENSE`, etc.) and top-level
  directories — no source files.
- **Namespace Safety**: Absolute imports use the `atlas.*` prefix,
  avoiding collisions with other packages.
- **Asset Organisation**: `assets/` is kept at the root, separate from
  source, and resolved at runtime via a `resource_path` helper that
  handles both development and PyInstaller bundled paths.
