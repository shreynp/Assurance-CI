# ADR-004: Migrate CI Test Generation to claude-code-action@v1

## Status: Accepted

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
  uses: anthropics/claude-code-action@v1
  with:
    anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
    prompt: "/test-generation"
    claude_args: |
      --max-turns 10
      --model claude-sonnet-4-6
  env:
    STORY_ID: ${{ steps.story.outputs.story_id }}
```

### Agentic loop inside the skill (`/test-generation`)

| Turn | What Claude does |
|------|-----------------|
| 1 | `cat jira/$STORY_ID.md` — read story + acceptance criteria |
| 2 | Check for `DOMAIN.md`; read ubiquitous language if present |
| 3 | `python scripts/build_context.py --base HEAD~1 --head HEAD --output /tmp/context.json` |
| 4–6 | Invoke `test-writer` sub-agent with story + domain context + build context; agent writes `generated/$STORY_ID/` |
| 7 | `pytest generated/$STORY_ID/ -v --tb=short` |
| 8–9 | Self-heal if failure: read output → fix test file → re-run (max 2 rounds) |
| 10 | Stop — downstream steps handle traceability |

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

**Not touched:** `scripts/append_record.py`, `scripts/resolve_gate.py`, `scripts/render_register.py`, `scripts/run_tests.py`, `src/domain/models.py`, `src/domain/register.py`, `src/domain/story_loader.py`

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
| Autonomous QA loop (§16) | Self-heal: read failure → fix → re-run, max 2 rounds |

---

## Consequences

**Easier:**
- Claude can read the story file, domain model, and related source before writing tests — tests are grounded in real context rather than a truncated diff string.
- Self-healing means transient generation errors don't fail the whole CI run.
- Sonnet is cheaper; cost drops from ~$0.50–1.00/run to ~$0.10–0.50/run.
- `generate_tests.py` still works for local dev (add `--context` for richer prompts).

**Harder:**
- CI runs now require the `anthropics/claude-code-action@v1` action, which is an external dependency.
- `--max-turns 10` is a budget cap; unusually complex stories may need this raised.
- The agentic loop is harder to unit-test than two deterministic SDK calls — behaviour is validated end-to-end by pushing a story-prefixed commit.
