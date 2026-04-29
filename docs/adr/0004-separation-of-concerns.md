# 4. Separation of Concerns: Pipeline & Worker
Date: 2026-02-18

## Context
As the application grew, the `Worker` class became monolithic, tightly coupling PyQt signal management with core business logic (scanning, estimation, backup). This made the code difficult to unit test without mocking the entire UI framework and reduced the reusability of the backup logic.

## Decision
I extracted the core backup logic into a separate, UI-agnostic `Pipeline` class. The `Worker` class now acts solely as an orchestrator, bridging the `Pipeline`'s callbacks to PyQt signals.

## Rationale
- **Testability**: The `Pipeline` can be instantiated and tested in isolation, verifying logic without initializing a `QApplication`.
- **Reusability**: The core logic is now portable and can be used in other contexts (e.g., a CLI tool or a different GUI framework) by simply providing different callbacks.
- **Maintainability**: Clear separation of concerns makes the codebase easier to understand and modify. Features related to the backup process go in `Pipeline`, while threading and UI communication go in `Worker`.
