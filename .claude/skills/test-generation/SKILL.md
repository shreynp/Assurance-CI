---
name: test-generation
description: >
  Generate and validate tests for a changed story. Use when running the assurance
  CI pipeline, when STORY_ID is set, or when asked to generate tests for a JIRA story.
  Handles context building, feature file creation, pytest/BDD/Playwright test generation,
  execution, and self-healing on failures. Invokes the test-writer agent for writing.
---

# Test Generation Skill

## Purpose

Orchestrate end-to-end test generation for a single JIRA story: build diff context,
generate a feature file + test script, run them, and self-heal on failure.

## Steps

### 1 — Read the story

```bash
cat ${JIRA_DIR:-jira}/$STORY_ID.md
```

`JIRA_DIR` is set by the CI workflow (e.g. `jira` or `assurance-ci/jira`); defaults to `jira` locally.

Extract: `title`, `description`, `acceptance_criteria`, `test_type`
(`test_type` is `pytest-bdd` or `playwright` — defaults to `pytest-bdd` if absent).

### 2 — Resolve DOMAIN.md

```bash
test -f DOMAIN.md && echo "exists" || echo "missing"
```

- **Exists** → Read `DOMAIN.md`; extract the ubiquitous-language table, entity field
  definitions, and domain events. Carry these into the test-writer agent prompt so
  Gherkin scenario names and assertions use the canonical terms (e.g. `story_id`,
  `commit_sha`, `gate_result`).
- **Missing** → Log: `⚠ DOMAIN.md not found — generating tests without ubiquitous language grounding.`
  Continue without it.

### 3 — Build incremental context

```bash
python scripts/build_context.py --base HEAD~1 --head HEAD --output /tmp/context.json --story-id $STORY_ID
cat /tmp/context.json
```

Read the resulting JSON:
- `changed_files` — files touched in this commit
- `changed_symbols` — top-level names that changed (AST-level), for both Python and TS/TSX
- `symbol_signatures` — full function/type signatures for each changed symbol (including TypeScript type annotations and return types)
- `callers` — first-level importers of changed modules (scans `app/`, `components/`, `lib/`, `hooks/`, `src/`, etc.)
- `context_type` — `"backend"`, `"ui"`, or `"both"`
- `diff_excerpts` — targeted diff lines per changed file
- `file_contents` — full source text of changed files under 200 lines (gives the model complete function bodies, not just the diff)
- `file_imports` — import specifiers declared inside each changed file (reveals dependencies that may need mocking)
- `file_directives` — `'use client'` / `'use server'` directives per TS/TSX file (determines whether a file is a React Client Component, Server Component, or API route)
- `existing_tests` — content of any co-located `.test.ts` / `.spec.tsx` / `__tests__/` files and previously generated tests for `$STORY_ID` in `generated/$STORY_ID/`

### 4 — Invoke the test-writer agent

Invoke the `test-writer` sub-agent with this combined context:

```
Story: <story title + acceptance criteria>
DOMAIN context (if DOMAIN.md present): <ubiquitous language table + entity field definitions>
Build context:
  changed_files: <list>
  changed_symbols: <dict>           # symbol names per file
  symbol_signatures: <dict>         # full type signatures per symbol — use these to know exact inputs/outputs to test
  callers: <dict>                   # files that import changed modules
  context_type: <backend|ui|both>
  diff_excerpts: <dict>
  file_contents: <dict>             # full source for small files — read before writing assertions
  file_imports: <dict>              # what each changed file imports — identify what to mock
  file_directives: <dict>           # 'use client'/'use server' — determines component type and test strategy
  existing_tests: <dict>            # extend these rather than generating from scratch if present

Write output to: generated/$STORY_ID/
  - generated/$STORY_ID/$STORY_ID.feature    (Gherkin)
  - generated/$STORY_ID/conftest.py          (shared fixtures — always generate this)
  - generated/$STORY_ID/test_$STORY_ID.py   (pytest-bdd or Playwright)
```

Rules passed to the agent:
- `story.test_type` determines whether to write `pytest-bdd` or `playwright` tests
- `context_type == "ui"` → always use Playwright even if `test_type` is unset
- Never modify `src/domain/` — those files are immutable from this skill
- `generated/$STORY_ID/` is the only write target
- When DOMAIN.md is present, use its ubiquitous-language terms verbatim in Gherkin
  scenario names and step text
- When DOMAIN.md is present, entity assertions must use field names from DOMAIN.md
  (e.g. `story_id`, `commit_sha`, `gate_result`, not ad-hoc names)

**Generated test conventions:**
- `scenarios()` must reference `"{STORY_ID}.feature"` by name — never a generic filename
- HTTP tests: always use `httpx`; always read `BASE_URL = os.environ.get("BASE_URL", "http://localhost:3000")`
- Auth tokens from env vars with safe defaults: `VALID_BEARER_TOKEN = os.environ.get("TEST_BEARER_TOKEN", "valid-test-token")`
- Never hardcode URLs or tokens — CI injects real values; local runs fall back to defaults
- The `context` fixture lives in `conftest.py` — the test file imports it, does not redefine it
- `conftest.py` must include the `httpx_safe` autouse fixture (see test-writer agent for template)

### 5 — Run generated tests

```bash
pytest generated/$STORY_ID/ -v --tb=short
```

### 6 — Self-heal on failure (max 2 rounds)

If pytest exits non-zero, diagnose by failure type before editing:

| Failure signature | Fix |
|-------------------|-----|
| `httpx.LocalProtocolError` | `conftest.py` `httpx_safe` fixture is missing or incomplete — regenerate it |
| `AssertionError` on status code | Re-read the actual API source; adjust assertion to match implementation; add a comment noting any AC mismatch |
| `StepNotImplementedError` / pending step | Add the missing `@given/@when/@then` to the test file |
| `ImportError` | Check `httpx` and `pytest-bdd` are installed (`pip show httpx pytest-bdd`) |
| `scenarios()` file not found | Verify the exact `.feature` filename matches the `scenarios()` call |

Edit only `generated/$STORY_ID/test_$STORY_ID.py` or `generated/$STORY_ID/conftest.py`.
Do NOT modify the `.feature` file — Gherkin is the AC source of truth.
Do NOT modify `src/domain/`.

### 7 — Write meta.json

After the tests pass (or after the final self-heal attempt), write
`generated/$STORY_ID/meta.json`. This file is required by `append_record.py`,
which reads it unconditionally and will raise `FileNotFoundError` if absent.

```json
{
  "feature_file": "generated/<STORY_ID>/<STORY_ID>.feature",
  "test_script": "generated/<STORY_ID>/test_<STORY_ID>.py"
}
```

Example for `STORY_ID=PROT-111`:
```json
{
  "feature_file": "generated/PROT-111/PROT-111.feature",
  "test_script": "generated/PROT-111/test_PROT-111.py"
}
```

Write this file regardless of whether tests passed or failed.

### 8 — Stop

Downstream workflow steps (`append_record.py`, `render_register.py`, git push,
`resolve_gate.py`) run outside this skill. Do not call them here.

## Environment

- `STORY_ID` — set by the CI workflow or by the user when running locally
- `JIRA_DIR` — directory containing story markdown files (default: `jira`)
- `BASE_URL` — live server URL for HTTP tests (default: `http://localhost:3000`)
- `TARGET_URL` — alias for `BASE_URL` used by some test patterns
- `TEST_BEARER_TOKEN` — auth token injected by CI for authenticated endpoint tests
- `ANTHROPIC_API_KEY` — required for the test-writer agent
- Output writes to `generated/$STORY_ID/`

## Local usage

```bash
STORY_ID=PROT-101 claude
# then type: /test-generation
```
