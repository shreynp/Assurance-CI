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
python scripts/build_context.py --base HEAD~1 --head HEAD --output /tmp/context.json
cat /tmp/context.json
```

Read the resulting JSON:
- `changed_files` — files touched in this commit
- `changed_symbols` — top-level names that changed (AST-level)
- `callers` — first-level importers of changed modules
- `context_type` — `"backend"`, `"ui"`, or `"both"`
- `diff_excerpts` — targeted diff lines

### 4 — Invoke the test-writer agent

Invoke the `test-writer` sub-agent with this combined context:

```
Story: <story title + acceptance criteria>
DOMAIN context (if DOMAIN.md present): <ubiquitous language table + entity field definitions>
Build context:
  changed_files: <list>
  changed_symbols: <dict>
  callers: <dict>
  context_type: <backend|ui|both>
  diff_excerpts: <dict>

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

### 6 — Classify failures: fix the test or report and stop

If pytest exits non-zero, read every `FAILED` / `ERROR` entry and classify before acting.
There are exactly two paths.

---

#### Category A — Test has a technical defect → fix it (max 2 rounds)

The test crashes before it can meaningfully assert, or it calls a Playwright/Python API
incorrectly. The feature may or may not be implemented correctly — you cannot tell yet.

Fix and re-run if ANY failure matches these signatures:

| Signature | Fix |
|-----------|-----|
| `Locator.inner_text: Error: Node is not an HTMLElement` | Test calls `.inner_text()` on an SVG node. Fix: use `.text_content()` instead, or add a hidden `<span data-testid="...">` mirror in the component (document the mismatch in a comment). |
| `StepNotImplementedError` / pending step | Add the missing `@given/@when/@then` step implementation. |
| `ImportError` / `ModuleNotFoundError` | Fix the import. |
| `scenarios()` `FileNotFoundError` | Verify the exact `.feature` filename matches the `scenarios()` call. |
| `httpx.LocalProtocolError` | Regenerate the `httpx_safe` autouse fixture in `conftest.py`. |
| Exception traceback points into `conftest.py` or a fixture function (not the test body) | Fix the fixture. |
| `AssertionError: Locator expected to be visible` for a `data-testid` that **does** exist somewhere on the page | The locator is too specific (e.g. scoped to the wrong ancestor). Broaden the selector. Confirm by running: `page.locator('[data-testid="<id>"]').count()` — if > 0 anywhere, it's a locator bug. |

Edit only `generated/$STORY_ID/test_$STORY_ID.py` or `generated/$STORY_ID/conftest.py`.
Do NOT modify the `.feature` file — Gherkin is the AC source of truth.
Do NOT modify `src/` or `src/domain/`.

---

#### Category B — Implementation does not meet AC → record and stop

The test ran correctly but the feature behaved differently than the AC specifies.
Do NOT iterate. Do NOT try to adjust assertions to match a broken implementation.

Stop immediately if the remaining failures show:

- `AssertionError` at an assertion line in the test body — the correct element was found but the value / state is wrong.
- `data-testid` genuinely absent from the DOM — confirmed by checking `page.locator('[data-testid="<id>"]').count() == 0` — meaning the feature is not implemented or is placed incorrectly in a way that the test cannot work around.
- Count / state mismatch after test setup completed without error (fixture / conftest ran cleanly, only the assertion failed).

For Category B:

1. Write `generated/$STORY_ID/gate_notes.md` with this structure:

```markdown
# Gate Notes — <STORY_ID>

## Implementation gaps found

| Test | AC covered | Expected | Observed |
|------|-----------|----------|----------|
| test_ac1_... | AC1: ... | element visible in header | element absent from DOM |
| ... | ... | ... | ... |

## Recommendation

The implementation does not yet satisfy the above acceptance criteria.
Run `/assurance-resolve` to fix the code and re-run assurance.
```

2. Write `meta.json` (step 7).
3. **Stop.** Do not call any more tools. The downstream workflow steps will record the
   gate-red result from the pytest report written by the separate "Run generated tests"
   workflow step.

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
