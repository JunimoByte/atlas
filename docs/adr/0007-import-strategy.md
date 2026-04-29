# 7. Import Strategy: Absolute Imports with atlas Prefix
Date: 2026-02-18

## Context
With the move to the `atlas` package structure, imports needed to be updated to reflect the new namespace.

## Decision
I updated all imports to use **absolute imports with `atlas.` prefix** (or relative imports within the package where appropriate).

## Rationale
- **Explicitness**: `from atlas.lib import browsers` clearly identifies the package origin.
- **Portability**: The code can be installed and imported in any environment without relying on `src` being in the `PYTHONPATH`.
- **Consistency**: Matches the directory structure and package name.
