# Contributing to Atlas

Thank you for your interest in Atlas.

Atlas is an open-source project licensed under the **GNU AGPL v3**. Code contributions are welcome! Please note that while all contributions are reviewed, there is no guarantee that a code contribution will be accepted. Community feedback, browser support suggestions, and feature ideas are also always welcome.

## How You Can Contribute

As an open-source project, you can help improve Atlas in many ways:

### Browser Support Suggestions

If you would like Atlas to support an additional browser, please include:

- **Browser name**
- **Version(s)**
- **Operating system**
- **Profile directory path** (if known)
- **Any special behavior** (portable mode, sandboxing, etc.)

This helps evaluate feasibility and compatibility.

### Feature Requests

When suggesting features, please include:

- A clear description of the problem
- The desired outcome
- Example workflow
- Platform relevance (Windows XP, Windows 7, modern Linux, etc.)

Atlas prioritizes:

- Stability
- Cross-platform reliability
- Backward compatibility
- Clean, maintainable architecture

### Bug Reports

If reporting an issue, include:

- Operating system and version
- Python version (if applicable)
- Steps to reproduce
- Expected behavior
- Actual behavior
- Logs (if available)

Reproducible reports are prioritized.

## Communication

Suggestions and feedback can be shared through official Atlas social channels.

Please keep communication respectful and constructive.

## Code Standards (Internal)

Atlas development follows:

- **PEP 8** for style
- **PEP 257** for docstrings
- Modular architecture principles
- Clear separation of UI and pipeline logic
- Backward compatibility constraints (Windows XP → Windows 11, glibc 2.23+)

These standards guide long-term maintainability.

## Development Tooling

Atlas development may use AI-assisted tools, including Claude and Gemini Pro, as part of the development workflow. 

**All AI-assisted output is treated as reference material.** It must be manually reviewed, validated, and, when necessary, modified or rewritten by the contributor before submission.

These tools are limited to supportive tasks such as:

- Drafting documentation
- Generating initial unit test scaffolding
- Suggesting test scenarios or edge cases
- Assisting with code suggestions and refactoring guidance


AI tools are not used to autonomously generate, modify, or commit production code. All changes to the repository are created and submitted manually by the contributor, and then reviewed by the maintainer.

AI-generated content does not constitute authorship. Contributors retain full responsibility for the code they submit, while the maintainer retains ultimate responsibility for what is merged into the Atlas repository.

## Pull Requests and Human Oversight

As an open-source project, it’s important to clarify how code contributions and reviews work:

- **All changes require human review.** No AI tool or automated system can directly commit code. Every change is manually evaluated by the maintainer.

- **PRs are evaluated for:**
  - Correctness and functionality
  - Cross-platform compatibility
  - Adherence to Atlas code standards (PEP 8, PEP 257, modular architecture)
  - Maintainability and readability

- **AI-assisted contributions** (unit tests, docs, test scenarios, etc.) are **treated as reference material only**. Contributors must manually validate, refine, and take ownership of all such output before submitting it for review.

- **Explainability and defense:** Contributors must fully understand and be able to justify every line of their code. AI-assisted output is allowed only as reference; you must be able to explain the implementation choices, reasoning, and design decisions during review. Contributions that cannot be confidently defended may be rejected, and repeated inability to explain code may result in temporary or permanent restriction from contributing.

- **Human accountability:** The contributor is accountable for the code they submit, while the maintainer retains responsibility for deliberating and verifying every change before it is merged. Nothing is merged without deliberate review by the maintainer.

- **No automated merges or autonomous commits** are allowed—Atlas values reliability and careful oversight over speed or automation.

This ensures Atlas stays **stable, secure, and maintainable**, even if AI tools are used as a helpful assistant rather than a decision-maker.

## Design Philosophy

Atlas is built with the following priorities:

1. **Reliability over rapid expansion**
2. **Cross-platform stability**
3. **Clean, expandable architecture**
4. **Defensive programming**
5. **Minimal unnecessary complexity**

## Future Plans

Atlas is committed to the open-source community. Future plans may include expanding the contribution model or adding new collaboration channels.

Atlas does not currently implement archive encryption.
Users are responsible for securing backup storage locations.

Thank you for supporting Atlas.

Your ideas help shape its direction.
