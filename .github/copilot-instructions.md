# AGENTS.md
Role: Ultra-dense output. Sacrifice grammar for token efficiency. Preserve meaning. Omit pleasantries.

## Project Overview
Assurance CI — story-to-gate traceability pipeline. Claude generates BDD tests from Jira story commits; tests run in CI; results written to `traceability/register.json`; Streamlit dashboard shows pass/fail per story.

## Tech Stack
- Python 3.12 · pytest-bdd (API tests) · Playwright Python (UI tests)
- Anthropic Claude (`anthropic` SDK) · Streamlit dashboard · GitHub Actions CI
- setuptools + pyproject.toml · virtualenv at `.venv/`

## Commands
```bash
source .venv/bin/activate && pip install -e ".[dev]"  # install
streamlit run src/dashboard/app.py                     # dashboard
pytest tests/ -v                                       # all tests
ruff check . && ruff format --check .                 # lint
./scripts/init.sh                                      # smoke test
python scripts/render_register.py                      # regenerate REGISTER.md
```

## Architecture Rules
- `src/domain/` is pure: no I/O, no external calls — all I/O lives in `scripts/`
- Seed data → `traceability/register.json` (not `_demo.json`); run `scripts/render_register.py` after
- GitHub Actions fallback `pip install`: verify package names against actual SDK imports in source
- Apply all fixes to existing files — do not create new files for bug fixes

## Testing Requirements
- New features require tests before marking complete
- Verify test pass via tool call before marking any task done
- BDD scenarios in `tests/features/` · step defs in `tests/step_defs/` · unit tests in `tests/test_*.py`

## Definition of Done
1. Tests pass (verified via tool call output)
2. `ruff check .` passes
3. PROGRESS.md updated
4. Docs updated if behaviour changed
5. `./scripts/init.sh` passes

## Session Start Protocol
1. Read PROGRESS.md
2. Run `./scripts/init.sh` — fix failures before new work
3. Check `docs/adr/` for relevant prior decisions
