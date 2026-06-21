# CLAUDE.md — Assurance CI

## Rules

- When a GitHub Actions workflow has a fallback `pip install` (after `pip install -e .`), verify every package name against the actual SDK import in the source before committing the workflow.
- Seed data for the dashboard goes directly into the live data file (`register.json`), not a separate `_demo.json`. Run `scripts/render_register.py` after seeding to regenerate `REGISTER.md`.
- The `src/domain/` modules are pure (no I/O, no external calls). Keep them that way — all I/O lives in `scripts/`.
