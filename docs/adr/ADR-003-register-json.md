# ADR-003: Single Source of Truth — register.json
## Status: Accepted

## Context
The traceability register needs to be queryable by the gate script, renderable to Markdown, and displayable in the Streamlit dashboard. Three options: (1) SQLite DB, (2) separate JSON files per run, (3) single append-only JSON array.

## Decision
Use a single `traceability/register.json` as the source of truth — a JSON array of run records. `scripts/render_register.py` generates `traceability/REGISTER.md` from it. The dashboard reads `register.json` directly.

## Consequences
- **Easier**: No DB setup. `register.json` is version-controllable and diffable. Gate and dashboard both read the same file. Demo seed data can be injected directly.
- **Harder**: No indexing — full scan on every load (acceptable at demo scale). Must run `render_register.py` after every change to keep REGISTER.md in sync. Agents must be reminded not to create separate `_demo.json` files.
