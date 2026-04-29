# 3. Code Standards: PEP 8 & PEP 257
Date: 2026-02-18
Last updated: 2026-03-16

## Context
To ensure long-term readability and consistency, the Atlas codebase must
adhere to well-defined and widely accepted coding standards.

## Decision
I adopted **PEP 8** for code style and **PEP 257** uniformly for all
docstrings — public and private alike. This policy is enforced via
`AGENTS.md` at the repository root.

## Rationale
- **Consistency**: A single docstring standard eliminates judgment calls
  about whether a symbol is "public enough" to warrant a different style.
- **Simplicity**: PEP 257 covers all necessary documentation needs for
  this project without the verbosity of Google Style or NumPy Style.
- **Tooling Support**: PEP 8 and PEP 257 are natively supported by
  standard linters (`pycodestyle`, `pydocstyle`) and major IDEs with no
  extra configuration.
- **Python 3.8 Compatibility**: All type hints use `typing` module
  constructs (`Optional`, `List`, `Dict`, `Tuple`) rather than built-in
  generics introduced in Python 3.9+.
