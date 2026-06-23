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
cat jira/$STORY_ID.md
```

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
  - generated/$STORY_ID/$STORY_ID.feature  (Gherkin)
  - generated/$STORY_ID/test_$STORY_ID.py  (pytest-bdd or Playwright)
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

### 5 — Run generated tests

```bash
pytest generated/$STORY_ID/ -v --tb=short
```

### 6 — Self-heal on failure (max 2 rounds)

If pytest exits non-zero:

1. Read the full pytest output
2. Identify the failing step(s) or assertion(s)
3. Edit `generated/$STORY_ID/test_$STORY_ID.py` to fix the issue
4. Re-run `pytest generated/$STORY_ID/ -v --tb=short`
5. Repeat once more if still failing — then stop and report the failure

Do NOT modify the `.feature` file during self-heal (Gherkin is the source of truth).
Do NOT modify `src/domain/` during self-heal.

### 7 — Stop

Downstream workflow steps (`append_record.py`, `render_register.py`, git push,
`resolve_gate.py`) run outside this skill. Do not call them here.

## Environment

- `STORY_ID` — set by the CI workflow or by the user when running locally
- `ANTHROPIC_API_KEY` — required for the test-writer agent
- Story files live in `jira/$STORY_ID.md`
- Output writes to `generated/$STORY_ID/`

## Local usage

```bash
STORY_ID=PROT-101 claude
# then type: /test-generation
```
