# ADR-001: Python + pytest-bdd as Test Stack
## Status: Accepted

## Context
The pipeline generates executable tests from Jira stories. Tests need to be readable by QA managers (non-engineers) as acceptance criteria, and executable by CI without setup overhead. Two approaches were viable: pytest-bdd (Gherkin scenarios) or plain pytest with docstrings.

## Decision
Use **pytest-bdd** for BDD acceptance tests and **Playwright Python** for UI flow tests. Both run under the same `pytest` runner, unified test report.

## Consequences
- **Easier**: Generated Gherkin features are readable by QA without Python knowledge. Step definitions reuse across stories. CI runs a single `pytest tests/` command.
- **Harder**: Step definition maintenance overhead when adding new sentence patterns. Playwright requires browser binaries (`playwright install chromium`).
