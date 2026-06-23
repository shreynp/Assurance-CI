# CI Architecture: Agentic Test Generation

How the Assurance CI pipeline invokes Claude, and what infrastructure is wired up inside the GitHub Actions runner.

---

## Invocation Flow

Opening or updating a pull request triggers `assurance.yml` in the Assurance-CI repo. The pipeline has two jobs: `assurance` (generate → run → record) and `gate` (pass/fail the deploy).

> The downstream `protect-ai` repo uses its own `assurance.yml` which triggers on **push** to any non-main branch. That workflow clones Assurance-CI into `assurance-ci/` and runs the same scripts against the protect app's dev server.

```
Developer opens PR (or pushes to non-main branch in protect-ai)
    │
    ▼
[assurance job]
    │
    ├─ commit_parser.extract_story_id()          ← deterministic Python
    │     no story ID → exit 0 (skip)
    │
    ├─ claude-code-action@v1                     ← agentic loop (max 10 turns)
    │     prompt: "/test-generation"
    │     env: STORY_ID=PROT-101
    │     │
    │     │  MCPs auto-loaded: context7, playwright, fetch
    │     │  Permissions: settings.json allowlist (no prompts)
    │     │
    │     └─ /test-generation skill executes:
    │           1. Read jira/PROT-101.md
    │           2. Check DOMAIN.md (ubiquitous language)
    │           3. Bash → build_context.py → /tmp/context.json
    │           4. Invoke test-writer sub-agent
    │                writes generated/PROT-101/PROT-101.feature
    │                writes generated/PROT-101/test_PROT-101.py
    │                [PostToolUse hook: ruff formats each .py after Write]
    │           5. Bash → pytest generated/PROT-101/ -v --tb=short
    │           6. On failure: Edit test → re-run (max 2 rounds)
    │                [Playwright MCP available for UI test self-heal]
    │           7. Stop — return control to workflow
    │
    ├─ append_record.py                          ← deterministic Python
    ├─ render_register.py                        ← deterministic Python
    ├─ git commit + push traceability artifacts  ← deterministic shell
    │     [pre-commit.sh: secrets check + domain purity check]
    └─ resolve_gate.py → /tmp/gate.json          ← deterministic Python
    │
    ▼
[gate job]
    └─ reads gate.json → exits 0 (green) or 1 (red)
```

---

## What Is Wired Up Inside the Runner

### MCPs — `.claude/mcp.json`

Auto-loaded by `claude-code-action@v1`. All three run as `npx` processes on the Actions runner; no separate install step is needed.

| MCP | Package | Role in CI |
|-----|---------|-----------|
| **context7** | `@upstash/context7-mcp` | Version-specific pytest-bdd and Playwright API docs — prevents hallucinated method signatures |
| **playwright** | `@anthropic-ai/mcp-playwright` | Actual browser control — Claude can launch Chromium, navigate, and assert on DOM during self-heal of UI tests |
| **fetch** | `@modelcontextprotocol/server-fetch` | Converts web pages to Markdown — fallback when context7 doesn't cover a library |

### Tools — `settings.json` allowlist

These tools run without permission prompts in CI. Defined in `.claude/settings.json`, which is checked into the repo and read by `claude-code-action@v1` automatically.

```
Bash(python scripts/*)   ← build_context.py, append_record.py, etc.
Bash(pytest *)           ← run and re-run generated tests
Bash(git diff*)          ← incremental context building
Bash(git log*)           ← history lookups
Bash(ruff check*)        ← lint checks
Read                     ← any file in the repo
Write                    ← any file (guarded by PostToolUse hook)
Edit                     ← any file (guarded by PostToolUse hook)
```

MCP tools (browser control, doc lookups, fetch) do not require separate allowlisting — they're covered by the MCP server declarations.

### Skills — `.claude/skills/test-generation/SKILL.md`

One skill is invoked in CI. The `prompt: "/test-generation"` field in `assurance.yml` is the entry point. Claude reads the skill file from the checked-out repo and follows its 7-step protocol:

1. Read the Jira story file (`jira/$STORY_ID.md`)
2. Resolve `DOMAIN.md` for ubiquitous language grounding
3. Run `build_context.py` → structured JSON (changed files, AST-level symbols, callers, diff excerpts)
4. Invoke the `test-writer` sub-agent with combined context
5. Run pytest against generated output
6. Self-heal on failure (max 2 rounds)
7. Stop — downstream steps handle traceability

The skill enforces two hard constraints: never modify `src/domain/`, and write only to `generated/$STORY_ID/`.

### Agents — `.claude/agents/`

Three agents exist. One is invoked per CI run:

| Agent | Invoked in CI? | Model | Allowed tools | Role |
|-------|---------------|-------|---------------|------|
| **test-writer** | ✅ Yes — Step 4 of the skill | sonnet | Read, Write, Edit, Grep, Glob, Bash | Writes `.feature` + `test_*.py` into `generated/$STORY_ID/` |
| **docs-writer** | No | haiku | Read, Write, Edit, Grep, Glob, Bash | Post-merge doc sync — used manually |
| **research-assistant** | No | sonnet | Read, Grep, Glob, Bash, WebSearch, WebFetch | Pre-integration library research — used manually |

`test-writer` receives story context, DOMAIN ubiquitous language (if present), and the structured build context dict. It has no write access outside `generated/`.

### Hooks — `.claude/settings.json` + `.claude/hooks/`

Two Claude hooks fire during the agentic loop:

| Hook type | Trigger | Script | Effect |
|-----------|---------|--------|--------|
| **PostToolUse** | After every `Write` or `Edit` | `format-file.sh` | Runs `ruff format` silently on `.py` files — zero agent tokens wasted on formatting |
| **PreToolUse** | Before every `Write` or `Edit` | inline `echo` | Reminds Claude: `src/domain/` must stay pure — I/O belongs in `scripts/` |

One git hook fires outside the agentic loop:

| Hook | When | Script | Checks |
|------|------|--------|--------|
| **pre-commit** | On `git commit` (traceability step) | `pre-commit.sh` | (1) Leaked secrets in staged diff — hard fail. (2) I/O imports added to `src/domain/` — hard fail. |

---

## Context Builder — `scripts/build_context.py`

Replaces the old raw `git diff HEAD~1 HEAD` dump (8 k cap, unstructured). Produces `/tmp/context.json`:

```json
{
  "changed_files": ["src/domain/generator.py"],
  "changed_symbols": {"src/domain/generator.py": ["build_feature_prompt"]},
  "callers": {"scripts/generate_tests.py": ["build_feature_prompt"]},
  "context_type": "backend",
  "diff_excerpts": {"src/domain/generator.py": "...targeted diff lines..."}
}
```

`context_type` routes test strategy: `"ui"` → always Playwright; `"backend"` → pytest-bdd; `"both"` → both.

---

## Prompt Builders — `src/domain/generator.py`

`build_feature_prompt(story, diff, context)` and `build_test_script_prompt(story, feature_text, feature_filename, context)` accept the structured context dict and append targeted sections (`## Changed Symbols`, `## Call Sites`, `## Test Surface`) so prompts are precise rather than a wall of diff text. The `context=None` path remains for backward compatibility and local use.

---

## Cost Profile

| Approach | Model | Calls | Estimated cost/run |
|----------|-------|-------|--------------------|
| Old (fixed SDK calls) | Opus | 2 fixed | ~$0.50–1.00 |
| New (agentic loop) | Sonnet | 3–10 turns | ~$0.10–0.50 |

Self-healing on the first attempt avoids a full re-run of the workflow (~6 min) at the cost of 1–2 additional turns (~$0.05).

---

## Jira File Format Contract

`jira/PROT-NNN.md` files are the source of truth for acceptance criteria. `src/domain/story_loader.py` extracts AC text using this pattern:

```
_AC_PATTERN = re.compile(r"^-\s+AC\d+:\s+(.+)$", re.MULTILINE)
```

**Every story file must have bullet-format AC lines immediately after `## Acceptance Criteria`:**

```markdown
## Acceptance Criteria

- AC1: Short machine-readable description of the criterion
- AC2: Another criterion
```

Prose-style bold headings (`**AC1 — Title**`) are for human readability and may coexist, but the parser ignores them. If no `- ACN:` bullets are present, `story_loader.py` raises `ValueError: No acceptance criteria found` and the CI run fails at the generate step.

When served via GitHub Pages, the URL is `https://shreynp.github.io/Assurance-CI/PROT-NNN.md` — fetched by `scripts/fetch_jira_ticket.py` using `JIRA_DATA_URL` env var.

---

## Local Usage

```bash
STORY_ID=PROT-101 claude
# then type: /test-generation
```

Claude picks up the same skill file, runs the identical 7-step loop with local tools. The Playwright MCP and context7 MCP are available locally too (via `.claude/mcp.json`).
