# Contributing to Assurance CI

## Architecture Layers

| Layer | Path | Rule |
|-------|------|------|
| **Domain** | `src/domain/` | Pure functions — no I/O, no external calls |
| **Scripts** | `scripts/` | All I/O — reads/writes files, calls Claude API |
| **Dashboard** | `src/dashboard/` | Streamlit UI — reads `register.json` and reports |

## Code Patterns

### Domain purity
`src/domain/` modules must have zero I/O and zero external calls. If you need to read a file or call an API, put it in `scripts/`.

### Register updates
Seed data goes directly into `traceability/register.json`. Always run `python scripts/render_register.py` after any `register.json` changes to regenerate `traceability/REGISTER.md`.

### Tests
```
tests/
  features/           # Gherkin .feature files (BDD scenarios)
  step_defs/          # Python step definitions — import from src/domain/ only
  test_*.py           # Unit tests
```
Run all: `pytest tests/ -v`

### Imports
Use direct imports — no barrel re-exports:
```python
from src.domain.models import StoryRun        # correct
from src.domain import StoryRun               # avoid
```

### GitHub Actions workflows
When adding fallback `pip install` steps, verify every package name against the actual SDK import in the source file. The Anthropic SDK imports as `anthropic`, not `anthropic-sdk`.

## Commit Conventions

Format: `[type]: [description]`
Types: `feat` / `fix` / `docs` / `test` / `chore` / `ci`

**Traceability commits must include `[skip ci]`** — the `assurance` job commits generated test files and register rows back to the repo mid-run. Without `[skip ci]`, that push triggers another pipeline run, creating a loop. The `append_record` and `render_register` git push steps already add this tag; preserve it if you edit those steps.

## Definition of Done
1. `pytest tests/ -v` — run it, read the output, confirm green
2. `ruff check .` passes
3. PROGRESS.md updated
4. No secrets in staged files
5. `./scripts/init.sh` passes
