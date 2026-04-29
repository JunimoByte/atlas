# 2. GUI Framework: PyQt (Qt)
Date: 2026-02-18

## Context
Atlas requires a graphical user interface that is professional, responsive, and visually consistent across all supported platforms without maintaining separate UI implementations.

## Decision
I selected **PyQt**, the Python bindings for the **Qt** framework.

## Rationale
- **Maturity**: Qt is a long-established, production-proven framework with a strong focus on stability and backward compatibility.
- **Native Look and Feel**: Qt integrates with platform-specific rendering and theming systems, allowing the application to respect system appearance settings.
- **Comprehensive Widget Set**: Qt provides a rich collection of high-quality widgets, reducing the need for custom UI implementations.
- **Future-Proofing**: Targeting the current long-term supported generation of the Qt framework aligns Atlas with its ongoing stability commitments.
