# ADR-004: Migrate CI Test Generation to claude-code-action@v1

## Status: Accepted (amended 2026-06-23, 2026-06-24)

## Context

The original `assurance.yml` called the Anthropic Python SDK directly with two fixed API calls per story:

1. `GET code diff` — raw `git diff HEAD~1 HEAD` piped to a file (8 000 char cap, silently truncated)
2. `Generate feature file + test script` — `generate_tests.py` made two sequential `client.messages.create` calls
3. `Run generated tests` — `run_tests.py` ran pytest and wrote a report

Problems with that approach:
- **Context blindness**: a raw diff string has no structure. Claude could not see which symbols changed, which modules imported them, or whether the change was UI or backend.
- **No self-healing**: if the generated test had a syntax error or a wrong step definition, CI failed with no recovery.
- **No tool access**: Claude could not read additional files, check docs, or inspect the repo to clarify ambiguities.
- **Fixed cost**: two Opus calls per run regardless of story complexity (~$0.50–1.00/run).

`anthropics/claude-code-action@v1` gives Claude the full tool suite (Read, Write, Edit, Bash, Agent) inside the GitHub Actions runner, enabling an agentic loop: build context → generate → run → self-heal.

---

## Decision

Replace the three steps above with a single `claude-code-action@v1` step that invokes the `/test-generation` skill. All downstream steps (`append_record`, `render_register`, git push, `resolve_gate`, gate job) are unchanged.

### New workflow step

```yaml
- name: Generate and validate tests
  if: steps.story.outputs.has_story == 'true'
  continue-on-error: true
  uses: anthropics/claude-code-action@v1
  with:
    anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
    prompt: "/test-generation"
    claude_args: |
      --max-turns 25
      --model claude-sonnet-4-6
  env:
    STORY_ID: ${{ steps.story.outputs.story_id }}
```

`continue-on-error: true` ensures the pipeline always reaches `append_record` / PR comment even if Claude exits at max turns — failure evidence is preserved rather than swallowed.

### Agentic loop inside the skill (`/test-generation`)

| Turn | What Claude does |
|------|-----------------|
| 1 | `cat jira/$STORY_ID.md` — read story + acceptance criteria |
| 2 | Check for `DOMAIN.md`; read ubiquitous language if present |
| 3 | `python scripts/build_context.py --story-id $STORY_ID --base HEAD~1 --head HEAD --output /tmp/context.json` |
| 4–6 | Invoke `test-writer` sub-agent with story + domain context + build context; agent writes `generated/$STORY_ID/` |
| 7 | `pytest generated/$STORY_ID/ -v --tb=short` |
| 8 | Report failures and stop — **no auto-heal** (see Amendment 1) |

### Model change

Switched from `claude-opus-4-8` (hardcoded in `generate_tests.py`) to `claude-sonnet-4-6`. Sonnet costs ~80% less and is sufficient for test generation + self-healing.

---

## Files Changed

| File | Change |
|------|--------|
| `.github/workflows/assurance.yml` | Replaced `Get code diff` + `Generate feature file + test script` + `Run generated tests` with single `claude-code-action@v1` step |
| `.claude/skills/test-generation/SKILL.md` | **Created** — orchestration skill invoked by the action |
| `scripts/build_context.py` | **Created** — incremental context builder (AST-level symbol extraction, caller tracing, `context_type` routing) |
| `.claude/settings.json` | **Created** — allowlists (`Bash(python scripts/*)`, `Bash(pytest *)`, etc.) + `PostToolUse[Write]` auto-format hook |
| `src/domain/generator.py` | Added `context: dict | None = None` param to `build_feature_prompt` and `build_test_script_prompt`; appends `## Changed Symbols`, `## Call Sites`, `## Test Surface` sections when context provided |
| `scripts/generate_tests.py` | Added `--context` CLI flag; loads `context.json` and passes it through to both prompt builders |
| `tests/test_build_context.py` | **Created** — 18 unit tests for `build_context.py` (mocked subprocess, no git required) |
| `tests/test_generator.py` | Added 8 tests for context-dict path in both prompt builders |

**Not touched:** `scripts/append_record.py`, `scripts/resolve_gate.py`, `scripts/render_register.py`, `scripts/run_tests.py`, `src/domain/models.py`, `src/domain/register.py`, `src/domain/story_parser.py`

---

## How `build_context.py` works

```
git diff --name-only <base> <head>
  → for each changed .py file:
      ast.parse() → extract top-level names present in diff
      git diff -- <file> → targeted diff lines for those names only
  → scan src/ and scripts/ for importers of changed modules (1 level, ast)
  → output context.json:
      {
        "changed_files": [...],
        "changed_symbols": {"src/domain/models.py": ["ExecutionReport"]},
        "callers": {"src/domain/register.py": ["append_record"]},
        "context_type": "backend" | "ui" | "both",
        "diff_excerpts": {"src/domain/models.py": "...targeted diff..."}
      }
```

`context_type` is derived from path heuristics: `dashboard/` → `"ui"`, `domain/` or `scripts/` → `"backend"`, both → `"both"`. The skill uses this to route between `pytest-bdd` and Playwright test generation.

---

## How the context dict flows into prompts

`generate_tests.py` (legacy SDK path) now accepts `--context /tmp/context.json`:

```bash
python scripts/build_context.py --base HEAD~1 --head HEAD --output /tmp/context.json
python scripts/generate_tests.py --story-id PROT-101 --diff /tmp/commit.diff \
  --context /tmp/context.json --out generated/
```

When `context` is passed, `build_feature_prompt` appends:

```
## Changed Symbols
src/domain/models.py: ExecutionReport

## Call Sites
src/domain/register.py: append_record
```

And `build_test_script_prompt` appends:

```
## Test Surface
context_type: backend, changed: src/domain/models.py
```

Without `--context` the script behaves identically to before — fully backward compatible.

---

## Why This Architecture

| Principle (agentic-guide-v7) | Application |
|------------------------------|-------------|
| Skills over inline prompts (§6) | `/test-generation` skill — keyword-rich description, trigger-activated |
| Wave Protocol (§8) | Skill (orchestrator) → `test-writer` agent (implementer) |
| Hooks as guardrails (§4) | `PostToolUse[Write]` auto-ruff; no agent tokens wasted on formatting |
| Model routing (§12) | Sonnet not Opus — ~80% cost reduction |
| Specific allowlists (§13) | `Bash(python scripts/*)` not blanket `Bash` |
| Autonomous QA loop (§16) | ~~Self-heal: read failure → fix → re-run, max 2 rounds~~ — removed (Amendment 1) |

---

## Consequences

**Easier:**
- Claude can read the story file, domain model, and related source before writing tests — tests are grounded in real context rather than a truncated diff string.
- `continue-on-error: true` means traceability evidence is always written, even when Claude hits the turn cap or a test fails.
- Sonnet is cheaper; cost drops from ~$0.50–1.00/run to ~$0.10–0.50/run.
- `generate_tests.py` still works for local dev (add `--context` for richer prompts).

**Harder:**
- CI runs now require the `anthropics/claude-code-action@v1` action, which is an external dependency.
- `--max-turns 25` is a budget cap; abnormally complex stories (many acceptance criteria, large diffs) may still hit it.
- The agentic loop is harder to unit-test than two deterministic SDK calls — behaviour is validated end-to-end by pushing a story-prefixed commit.

---

## Amendments

### Amendment 1 — Auto-heal loop removed (2026-06-23, commit `2f284cf`)

**Change:** The skill's self-heal loop (read failure → fix test file → re-run, max 2 rounds) was removed. The skill now runs tests once, reports failures, and stops.

**Reason:** Auto-heal consumed turns non-deterministically (always ≥2 extra turns on any failure), masked real acceptance-criteria gaps by producing a forced-green test rather than surfacing the true reason the generated test failed, and made CI behaviour hard to explain to approvers. A test that fails because the implementation is wrong should fail — not be silently fixed into a green.

**Impact:** Turn budget reduced; turn cap lowered from the originally planned 10 but raised to 25 (`--max-turns 25`) to give multi-file test generation enough headroom without the heal rounds.

---

### Amendment 2 — TS/TSX AST support in `build_context.py` (2026-06-24, commit `823ccda`)

**Change:** `build_context.py` was Python-only for AST parsing. All TS/TSX/JS/JSX changed files produced empty `changed_symbols`, `callers`, and `diff_excerpts`.

**Fix:** Added full tree-sitter TS/TSX/JS/JSX support — `_ts_parser()`, `_ts_decl_name()`, `changed_symbols_ts()`, `find_ts_callers()`. Added `tree-sitter` and `tree-sitter-typescript` to `pyproject.toml`. Widened `context_type` classifier to recognise `components/`, `app/`, `api/`, `lib/` path segments (Next.js structure).

**Impact:** Context is now meaningful for the Protect AI (Next.js) codebase, which is entirely TS/TSX.

---

### Amendment 3 — Richer build context (2026-06-24, commit `bc31004`)

**Change:** Added 5 new fields to `context.json`:

| Field | Content |
|-------|---------|
| `symbol_signatures` | Full TS/Python type signatures per changed symbol |
| `file_contents` | Full source for files ≤200 lines |
| `file_imports` | Import specifiers declared in each changed file |
| `file_directives` | `'use client'`/`'use server'` per TS/TSX file (Next.js component type) |
| `existing_tests` | Co-located `.test.ts`/`.spec.tsx`/`__tests__/` files + prior generated tests from `generated/$STORY_ID/` |

Also fixed `find_ts_callers` to scan `app/`, `components/`, `lib/`, `hooks/`, `stores/`, `pages/` instead of `src/` (which is empty in Next.js projects).

---

### Amendment 4 — RCA in PR report (2026-06-24, commit `bdc2972`)

**Change:** `build_pr_body.py` now adds a Root Cause Analysis section when any tests fail. Two layers: (1) static RCA table parsed from `pytest --tb=short` output (test name, one-line exception, first ≤3 assertion lines); (2) Claude Haiku-generated plain-English summary blockquote explaining likely root cause and recommending a fix. Haiku call fails silently — the table always renders.

**Impact:** Approvers can read the PR body to understand *why* the gate is red without opening the raw test log.
