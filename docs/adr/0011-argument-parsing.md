# 11. Command-Line Argument Parsing: atlas.args

Date: 2026-09-19

## Status

Accepted

## Context

With the introduction of headless CLI mode (`--cli`) and version reporting (`-v`, `--version`), command-line argument configuration was initially declared directly inside `src/atlas/main.py`.

As additional flags and options are planned (e.g. output directory overrides, quiet modes, format selectors), having argument schemas, version constants, and help text defined inside `main.py` violates the Single Responsibility Principle and bloats the application's primary bootstrapper router.

## Decision

We isolate all command-line parsing, argument definitions, and version metadata into a dedicated module: `src/atlas/args.py`.

1. **Dedicated Module (`atlas.args`)**:
   - Dynamically resolves application version from `pyproject.toml` via `get_version()`, eliminating hardcoded constants and preventing circular imports.
   - Constructs and configures the `argparse.ArgumentParser` via `build_parser()`.
   - Exposes `parse_args(argv=None)` to parse arguments gracefully (handling known options and tolerating unknowns where applicable).
2. **Minimal Bootstrapper (`atlas.main`)**:
   - `main.py` imports `parse_args` and retains strictly entry routing logic (directing execution to `atlas.cli` or `atlas.gui`).
   - Zero argument setup code lives in `main.py`.

## Rationale

- **Maintainability & Extensibility**: Adding new flags in the future requires editing only `atlas.args`, keeping `main.py` lean, stable, and focused solely on process routing.
- **Single Source of Truth**: Centralizes version and CLI definition in one place, avoiding duplicate argument definitions or constants across entry points.
- **Isolated Testability**: The argument parsing logic can be thoroughly unit-tested in isolation (`test_args.py`) without needing to mock application runners or Qt initializers.
