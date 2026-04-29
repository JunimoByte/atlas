## Purpose

This document defines the **strict coding standards** used in this repository.
Agents, contributors, and automated systems must follow these rules when
generating, reviewing, or modifying code.

All Python code must comply with:

* **PEP 8** (style and formatting)
* **PEP 257** (docstrings)
* **Python 3.8 compatibility**

Code that violates these rules should be considered **non-compliant**.

---

# 1. Python Version Compatibility

All code must run on **Python 3.8+** without modification.

## Allowed

* f-strings
* dataclasses
* typing module
* walrus operator (`:=`)
* TypedDict

## Disallowed (3.9+ or later features)

Do **not** use:

### Built-in generics

```python
list[str]
dict[str, int]
```

Use:

```python
from typing import List, Dict

List[str]
Dict[str, int]
```

### Union pipe syntax

```python
str | None
```

Use:

```python
Optional[str]
```

### Pattern matching

```python
match value:
    case 1:
```

### Exception groups

```python
except* Exception
```

### New standard library modules introduced after Python 3.8.

---

# 2. File Structure

Every module must follow this order:

```
Module docstring

Imports

Constants

Classes

Functions
```

Example structure:

```python
"""
Module description.
"""

# =============================================================================
# IMPORTS
# =============================================================================

import os
import logging
from typing import Optional


# =============================================================================
# CONSTANTS
# =============================================================================

MAX_RETRIES = 3


# =============================================================================
# CLASSES
# =============================================================================


class Example:
    """Example class."""


# =============================================================================
# FUNCTIONS
# =============================================================================


def run():
    """Run the module."""
```

---

# 3. PEP 8 Style Rules

## Indentation

* Use **4 spaces**
* Never use tabs

## Line Length

* Maximum line length: **79 characters**
* Docstrings and comments: **72 characters**

Long statements must be wrapped with parentheses.

```
result = (
    very_long_function(argument_one, argument_two)
)
```

---

## Blank Lines

Use:

* **2 blank lines** between top-level functions
* **1 blank line** between class methods
* **1 blank line** after imports

---

## Imports

Imports must be grouped in this order:

1. Standard library
2. Third-party libraries
3. Local modules

Example:

```python
import os
import sys

import requests

from atlas.backup import worker
```

Rules:

* One import per line
* Imports only at the top of the file

---

## Naming Conventions

| Element         | Style               |
| --------------- | ------------------- |
| Variables       | snake_case          |
| Functions       | snake_case          |
| Modules         | snake_case          |
| Classes         | PascalCase          |
| Constants       | UPPER_CASE          |
| Private members | _leading_underscore |

Example:

```python
MAX_BUFFER = 1024


class BackupManager:
    pass


def run_backup():
    pass
```

---

## Spacing Rules

### Around operators

```
x = a + b
value = width * height
```

### After commas

```
a, b, c
```

### No spaces inside parentheses

Incorrect:

```
func( a, b )
```

Correct:

```
func(a, b)
```

---

## Default Arguments

No spaces around `=` in defaults.

Incorrect:

```
def test(a = 5):
```

Correct:

```
def test(a=5):
```

---

## Comparisons

Use identity comparison for `None`.

Correct:

```
if value is None:
if value is not None:
```

Incorrect:

```
if value == None
```

---

## Boolean Checks

Prefer implicit truth checks.

Correct:

```
if items:
```

Avoid:

```
if len(items) > 0:
```

---

## Trailing Commas

Trailing commas are recommended in multi-line structures.

```
data = [
    "a",
    "b",
    "c",
]
```

---

# 4. PEP 257 Docstring Rules

All public modules, classes, and functions must include docstrings.

Docstrings must use **triple double quotes**.

```
"""
Summary sentence.
"""
```

---

## Module Docstrings

The first statement in every file.

```
"""
Atlas backup utilities.
Handles browser profile backups.
"""
```

---

## Function Docstrings

Format:

```
Summary line.

Detailed explanation.

Args:
    param: Description.

Returns:
    Description.
```

Example:

```python
def copy_file(src: str, dst: str) -> None:
    """
    Copy a file safely.

    Args:
        src: Source file path.
        dst: Destination file path.
    """
```

---

## One-Line Docstrings

Used for simple functions.

```
def is_valid() -> bool:
    """Return True if configuration is valid."""
```

Rules:

* Imperative mood
* One sentence
* Ends with a period

---

## Class Docstrings

Classes must include a description of their responsibility.

```
class BackupManager:
    """
    Controls backup tasks and worker execution.
    """
```

---

# 5. Type Hint Requirements

All public functions should include **type hints**.

Use the `typing` module.

Example:

```
from typing import Optional, List, Dict
```

Example function:

```
def load_profiles(paths: List[str]) -> Dict[str, str]:
```

Optional values:

```
Optional[str]
```

---

# 6. Logging

Use the `logging` module instead of `print()`.

Example:

```
import logging

LOGGER = logging.getLogger(__name__)

LOGGER.info("Backup started")
```

---

# 7. Nesting Depth

Avoid deep nesting.

Maximum recommended nesting depth:

```
3–4 levels
```

If exceeded, refactor logic into separate functions.

---

# 8. Code Clarity

Code must prioritize:

* readability
* maintainability
* explicit logic

Avoid:

* overly complex expressions
* hidden side effects
* unnecessary abbreviations

Prefer descriptive names and small functions.

---

# Compliance Summary

All generated or modified code must satisfy:

* PEP 8 formatting rules
* PEP 257 docstring structure
* Python 3.8 compatibility
* typing usage from `typing`
* consistent module layout

# Unit Tests

All code must include unit tests. To run them, use the existing venv:

```bash
.\venv\Scripts\python.exe -m pytest src/atlas/tests/unit --tb=short -q
```

Non-compliant code must be corrected before merging.