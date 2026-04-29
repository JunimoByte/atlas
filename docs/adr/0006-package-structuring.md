# 6. Package Structuring: atlas Package
Date: 2026-02-18
Last updated: 2026-03-16

## Context
To conform to Python packaging best practices and support proper
installation via `pip`, the codebase is encapsulated in a named package
under the `src/` directory.

## Decision
All source code lives under `src/atlas/`. The package is declared in
`pyproject.toml` using `hatchling` as the build backend. The top-level
`atlas` namespace exposes subpackages for each concern:

- `atlas.backup` — scanning, size estimation, compression, and backup
- `atlas.display` — window, controller, worker, signals, and controls
- `atlas.lib` — shared utilities (theme helpers, OS integration)
- `atlas.ui` — Qt dialog definitions

## Rationale
- **Packaging Standard**: Conforms to the `src/package-name` layout
  recommended by the Python Packaging Authority.
- **Namespace Cleanliness**: All internal imports use the `atlas.*`
  prefix (e.g., `from atlas.lib.themes import resource_path`), which is
  unambiguous and collision-safe.
- **Distributability**: The package can be installed with `pip install .`
  or bundled with PyInstaller without modifying `sys.path` or relying on
  a custom launcher.
- **Discoverability**: Each subpackage has an `__init__.py` that exports
  its public surface, making IDE navigation and type checking reliable.
