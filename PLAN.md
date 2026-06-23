# Plan: AI Test Generation via claude-code-action@v1

## Context

The current `assurance.yml` calls the Anthropic Python SDK directly — two fixed API calls per story, raw `git diff` as context (8k cap, silently truncated), no self-healing, no tool access. The research report recommended `anthropics/claude-code-action@v1` but it was never wired in.

Switching to `claude-code-action@v1` gives Claude the full tool suite (Read, Write, Edit, Bash, Agent) so it can: build context intelligently, generate tests, run them, observe failures, and fix them — all in one agentic loop. The existing Python scripts (`append_record`, `resolve_gate`, `render_register`) stay as-is because they don't need AI. Only the "generate → run → fix" middle is replaced.

---

## What Changes and What Stays

**Replaced with claude-code-action@v1:**
- `Get code diff` step (raw `git diff HEAD~1 HEAD`) → Claude runs `build_context.py` via Bash tool
- `Generate feature file + test script` step → Claude invokes `/test-generation` skill
- `Run generated tests` step → Claude runs pytest via Bash tool and self-heals on failure

**Stays as direct Python script calls:**
- Story ID extraction (`commit_parser`)
- `append_record.py` — traceability, no AI needed
- `render_register.py` — markdown render, no AI needed
- Commit traceability artifacts — git push
- `resolve_gate.py` — deterministic, no AI needed
- Gate evaluation job — unchanged

---

## How Skills, Hooks, Agents, and Scripts Work in claude-code-action@v1

| Feature | How it works in CI | Used here |
|---------|-------------------|-----------|
| **Skills** | `prompt: "/test-generation"` → Claude reads `.claude/skills/test-generation/SKILL.md` from the checked-out repo | Yes — primary entry point |
| **Hooks** | `.claude/settings.json` checked into repo; `PostToolUse[Write]` shell commands run on the Actions runner | Yes — auto-ruff on write |
| **Agents** (sub) | Claude can spawn `.claude/agents/test-writer.md` as a sub-agent during the skill run | Yes — test-writer writes tests |
| **Scripts** | Claude calls `python scripts/build_context.py` via Bash tool (allowlisted) | Yes — incremental context |
| **MCP** | `.claude/mcp.json` auto-loaded; context7 available | Yes — for pytest-bdd/playwright API docs |

---

## Phased Implementation

Each phase ends with `/triple-agent-audit` before the next phase starts. Commit each phase's deliverables with `/ship-it`. Between phases (multi-session work), run `/session-handoff` to persist state before `/clear`.

---

### Phase 1: `scripts/build_context.py` + `.claude/settings.json`

**Goal:** Incremental context builder + project allowlists so Claude can run tools in CI without permission prompts.

**Deliverables:**

**`scripts/build_context.py`** — stateless, pure-Python, per-run (no persistent index):
```
git diff --name-only <base> <head>
  → for each changed .py file:
      ast.parse() → extract top-level names changed in diff
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
CLI: `python scripts/build_context.py --base HEAD~1 --head HEAD --output context.json`

**`.claude/settings.json`** — checked into repo, applies in CI:
```json
{
  "permissions": {
    "allow": [
      "Bash(python scripts/*)",
      "Bash(pytest *)",
      "Bash(git diff*)",
      "Bash(git log*)",
      "Bash(ruff check*)",
      "Read",
      "Write",
      "Edit"
    ]
  },
  "hooks": {
    "PostToolUse": [{
      "matcher": "Write|Edit",
      "hooks": [{
        "type": "command",
        "command": "./.claude/hooks/format-file.sh \"${CLAUDE_TOOL_INPUT_FILE_PATH}\""
      }]
    }]
  }
}
```

**`tests/test_build_context.py`** — unit tests:
- Mock `subprocess.run` → verify changed-file detection
- Fixture: two Python files (one imports the other) → verify caller tracing
- `context_type` routing: `src/dashboard/` → "ui", `src/domain/` → "backend"
- Empty diff → graceful `{"changed_files": [], ...}`

**Commit:** `/ship-it` — stages `scripts/build_context.py`, `.claude/settings.json`, `tests/test_build_context.py`

**Triple audit gate:** `/triple-agent-audit` on Phase 1 before Phase 2

---

### Phase 2: `.claude/skills/test-generation/SKILL.md`

**Pre-condition:** Run `/domain-model` if `DOMAIN.md` is absent or has not been updated since new entities were introduced. Phase 2 reads DOMAIN.md for ubiquitous language — a stale or missing model produces tests with wrong field names.

**Goal:** The skill Claude invokes via `/test-generation` in CI — primary orchestration layer.

**File:** `.claude/skills/test-generation/SKILL.md`

Frontmatter:
```yaml
---
name: test-generation
description: >
  Generate and validate tests for a changed story. Use when running the assurance
  CI pipeline, when STORY_ID is set, or when asked to generate tests for a JIRA story.
  Handles context building, feature file creation, pytest/BDD/Playwright test generation,
  execution, and self-healing on failures. Invokes the test-writer agent for writing.
---
```

Skill body instructs Claude to:
1. Read `jira/$STORY_ID.md` — story title, acceptance criteria, test_type
2. **Resolve DOMAIN.md** — check if `DOMAIN.md` exists (Bash: `test -f DOMAIN.md`):
   - **Exists** → Read it; extract ubiquitous language table, entity field definitions, domain events
   - **Missing** → Log a warning ("DOMAIN.md not found — generating tests without ubiquitous language grounding"); continue without it
3. Run `python scripts/build_context.py` via Bash → read `/tmp/context.json`
4. Invoke `test-writer` sub-agent with: story + DOMAIN context (ubiquitous language + entity fields, if available) + build context → writes `generated/$STORY_ID/`
5. Run `pytest generated/$STORY_ID/ -v --tb=short` via Bash
6. Self-heal on failure: read output, fix test file, re-run (max 2 rounds)
7. Stop — downstream workflow steps handle traceability

Rules embedded in skill:
- `story.test_type` determines pytest-bdd vs Playwright
- `context_type` from context.json determines which modules to cover
- Never modify `src/domain/` — immutable from this skill
- `generated/$STORY_ID/` is the only write target
- When DOMAIN.md is present, use its ubiquitous-language terms verbatim in Gherkin scenario names and step text
- When DOMAIN.md is present, assertions against entities must use field names from DOMAIN.md (e.g. `story_id`, `commit_sha`, `gate_result`)

**Commit:** `/ship-it` — stages `.claude/skills/test-generation/SKILL.md`

**Triple audit gate:** `/triple-agent-audit` on Phase 2 before Phase 3

---

### Phase 3: `src/domain/generator.py` — structured context in prompts

**Goal:** Update prompt builders to accept structured context dict (for local dev and test-writer agent use).

**Changes:**
- `build_feature_prompt(story, context: dict | None = None)` — adds `## Changed Symbols` and `## Call Sites` sections when context dict provided
- `build_test_script_prompt(story, feature_file, context: dict | None = None)` — adds `## Test Surface` line
- `context=None` path unchanged (backward compat)

**Triple audit gate:** `/triple-agent-audit` on Phase 3 before Phase 4

---

### Phase 4: Rewrite `.github/workflows/assurance.yml`

**Goal:** Replace generate+run steps with a single `claude-code-action@v1` step.

Key change — replace these steps:
```yaml
# REMOVED:
- name: Get code diff
  run: git diff HEAD~1 HEAD -- . > /tmp/commit.diff

- name: Generate feature file + test script
  run: python scripts/generate_tests.py --story-id "$STORY_ID" --diff /tmp/commit.diff --out generated/

- name: Run generated tests
  run: python scripts/run_tests.py ...
```

With:
```yaml
# NEW:
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

Notes:
- No `--allowedTools` needed — `.claude/settings.json` (Phase 1) grants all required permissions
- `--max-turns 10`: read story (1) + build context (1) + test-writer agent (3-4) + run tests (1) + self-heal if needed (2)
- `STORY_ID` env var available to Claude and to `build_context.py`
- `claude-sonnet-4-6` replaces hardcoded `claude-opus-4-8` — ~80% cost reduction
- Context7 MCP auto-loaded for pytest-bdd/playwright API docs lookups

All downstream steps (`append_record`, `render_register`, commit, `resolve_gate`, gate job) unchanged.

**Triple audit gate:** `/triple-agent-audit` on Phase 4 (final)

---

## Files Modified

| File | Phase | Change |
|------|-------|--------|
| `scripts/build_context.py` | 1 | **Create** — incremental context builder |
| `.claude/settings.json` | 1 | **Create** — allowlists + PostToolUse hook |
| `tests/test_build_context.py` | 1 | **Create** — unit tests |
| `.claude/skills/test-generation/SKILL.md` | 2 | **Create** — CI orchestration skill |
| `src/domain/generator.py` | 3 | Add context dict param to prompt builders |
| `tests/test_generator.py` | 3 | Add tests for context-dict path |
| `.github/workflows/assurance.yml` | 4 | Replace generate+run steps with claude-code-action |

**Not touched:** `scripts/append_record.py`, `scripts/resolve_gate.py`, `scripts/render_register.py`, `scripts/run_tests.py`, `src/domain/models.py`, `src/domain/register.py`, `src/domain/story_loader.py`

---

## Why This Architecture (per agentic-guide-v7)

| Principle | Application |
|-----------|-------------|
| Skills over inline prompts (§6) | `/test-generation` skill — keyword-rich description, trigger-activated, under 500 lines |
| Wave Protocol (§8) | Skill (orchestrator) → test-writer agent (implementer) — separation of roles |
| Hooks as guardrails (§4) | `PostToolUse[Write]` auto-formats; no agent tokens wasted on formatting |
| Model routing (§12) | Sonnet (12x cost) not Opus (60x) for test gen — 80% savings |
| Specific allowlists (§13) | `Bash(python scripts/*)` not blanket Bash |
| Autonomous QA loop (§16) | Self-heal: read failure → fix → re-run, max 2 rounds |

---

## Verification

1. **Phase 1**: `python scripts/build_context.py --base HEAD~1 --head HEAD` → inspect JSON; `pytest tests/test_build_context.py -v`
2. **Phase 2 (DOMAIN.md present)**: Run locally with `STORY_ID=PROT-101 claude` → type `/test-generation` → skill reads DOMAIN.md, invokes test-writer with ubiquitous language context, tests generated with correct entity field names
2a. **Phase 2 (DOMAIN.md absent)**: Temporarily rename DOMAIN.md → re-run → skill logs warning and continues; generated tests should still pass but may use generic field names
3. **Phase 3**: `pytest tests/test_generator.py -v` — all tests pass including new context-dict path
4. **Phase 4**: Push a commit with `PROT-101:` prefix → GHA runs claude-code-action → skill generates+validates tests → downstream steps record + gate
5. **Cost**: ~$0.10–0.50/run (Sonnet, 10 turns) vs ~$0.50–1.00 (Opus, 2 fixed calls) — cheaper + self-healing
