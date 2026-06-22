# Architecture Decision Records

This directory contains ADRs (Architecture Decision Records) for Assurance CI.

ADRs document significant architectural decisions: why they were made, what alternatives were considered, and what tradeoffs were accepted. Without ADRs, agents will "improve" code by reversing deliberate choices.

## Index

| ADR | Title | Status |
|-----|-------|--------|
| [ADR-001](ADR-001-python-pytest-bdd.md) | Python + pytest-bdd as test stack | Accepted |
| [ADR-002](ADR-002-domain-purity.md) | Domain layer purity (no I/O in src/domain/) | Accepted |
| [ADR-003](ADR-003-register-json.md) | Single source of truth: register.json | Accepted |

## Template

```markdown
# ADR-NNN: [Title]
## Status: [Proposed | Accepted | Deprecated | Superseded by ADR-NNN]
## Context
[What motivated this decision?]
## Decision
[What was decided?]
## Consequences
[What becomes easier? What becomes harder?]
```
