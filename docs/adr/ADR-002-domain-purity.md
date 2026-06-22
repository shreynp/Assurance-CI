# ADR-002: Domain Layer Purity (No I/O in src/domain/)
## Status: Accepted

## Context
Early prototypes mixed file reading, Claude API calls, and business logic in single scripts. This made unit testing nearly impossible and caused coupling between I/O concerns and domain logic.

## Decision
`src/domain/` modules are **pure**: no file I/O, no network calls, no `subprocess`. All I/O lives in `scripts/`. Domain functions receive data as arguments and return data as results.

## Consequences
- **Easier**: Unit tests for domain logic run instantly without mocking. Domain modules are deterministic and side-effect-free. Agent changes to domain modules cannot accidentally introduce I/O.
- **Harder**: All orchestration code must live in scripts/, which can grow verbose. Pre-commit hook enforces this — see `.claude/hooks/pre-commit.sh`.
