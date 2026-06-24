# CI Architecture: Agentic Test Generation

How the Assurance CI pipeline invokes Claude, and what infrastructure is wired up inside the GitHub Actions runner.

---

## Invocation Flow

Three events trigger `assurance.yml` in the Assurance-CI repo:
- **`pull_request`** — any PR open/sync against any branch
- **`workflow_dispatch`** — manual run from the Actions UI or CLI, with an optional `story_id` input that overrides commit-message detection
- **Push to non-main in protect-ai** — the downstream `protect-ai` repo's own `assurance.yml` triggers on push, clones Assurance-CI into `assurance-ci/`, and runs the same scripts against the protect app's dev server

> ⚠️ **Known limitation — `pull_request` does not fire for GITHUB_TOKEN-created PRs**
>
> GitHub suppresses `pull_request` events (including `synchronize`) for any action performed
> by `GITHUB_TOKEN`. Since the Assurance CI workflow auto-creates PRs using
> `GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}`, that PR's `opened` event is swallowed and
> subsequent human pushes to the same branch may also not reliably fire `synchronize`.
>
> **Workaround (reliable today):** use `workflow_dispatch` to manually trigger the pipeline:
> ```bash
> gh workflow run assurance.yml --ref <branch> --field story_id=PROT-NNN
> ```
> **Permanent fix:** replace `secrets.GITHUB_TOKEN` with a dedicated PAT stored as
> `ACTIONS_PAT` — events triggered by a PAT do fire `pull_request` workflow triggers.
> Alternatively, open the PR manually before pushing commits (not via the workflow).

The pipeline has two jobs: `assurance` (generate → run → record → PR comment) and `gate` (pass/fail the deploy).

**Required permissions** (declared in `assurance.yml`):
```yaml
permissions:
  contents: write       # commit traceability artifacts back to the repo
  pull-requests: write  # create or comment on the assurance PR
  id-token: write       # OIDC auth (Workload Identity Federation for cloud resources)
```

**Manual dispatch via CLI:**
```bash
gh workflow run assurance.yml --ref <branch> --field story_id=PROT-105
```

```
Developer opens PR  OR  workflow_dispatch  OR  push to non-main (protect-ai)
    │
    ▼
[assurance job]
    │
    ├─ checkout (fetch-depth: 0, token: GITHUB_TOKEN)
    │
    ├─ commit_parser.extract_story_id()          ← deterministic Python
    │     priority: DISPATCH_STORY_ID → git commit → PR title → branch name
    │     no story ID found → exit 0 (skip)
    │
    ├─ fetch_jira_ticket.py                      ← deterministic Python
    │     fetches ${JIRA_DATA_URL}/PROT-NNN.md from GitHub Pages
    │     writes to jira/ for downstream steps
    │
    ├─ claude-code-action@v1                     ← agentic loop (max 25 turns)
    │     prompt: "/test-generation"
    │     env: STORY_ID=PROT-101, JIRA_DIR=jira, BASE_URL=http://localhost:3000
    │     │
    │     │  MCPs auto-loaded: context7, playwright, fetch
    │     │  Permissions: settings.json allowlist (no prompts)
    │     │
    │     └─ /test-generation skill executes:
    │           1. Read ${JIRA_DIR:-jira}/PROT-101.md
    │           2. Check DOMAIN.md (ubiquitous language)
    │           3. Bash → build_context.py → /tmp/context.json
    │           4. Invoke test-writer sub-agent
    │                writes generated/PROT-101/PROT-101.feature
    │                writes generated/PROT-101/conftest.py
    │                writes generated/PROT-101/test_PROT-101.py
    │                [PostToolUse hook: ruff formats each .py after Write]
    │           5. Bash → pytest generated/PROT-101/ -v --tb=short
    │           6. On failure: classify each failure (Locator bug /
    │                Implementation gap / Test infrastructure) →
    │                write generated/PROT-101/gate_notes.md → STOP.
    │                No auto-heal. No re-run. No edits.
    │           7. Write generated/PROT-101/meta.json (always)
    │           8. Stop — return control to workflow
    │
    ├─ append_record.py                          ← deterministic Python
    ├─ render_register.py                        ← deterministic Python
    ├─ git commit + push traceability artifacts  ← deterministic shell
    │     [pre-commit.sh: secrets check + domain purity check]
    │     commit message includes [skip ci] to prevent re-triggering the pipeline
    ├─ resolve_gate.py → /tmp/gate.json          ← deterministic Python (continue-on-error)
    ├─ build_pr_body.py → /tmp/pr_body.md        ← deterministic Python + Claude Haiku
    │     renders gate status, test results, and story link into PR markdown;
    │     when failures > 0: parses pytest --tb=short output into an RCA table
    │     (test name, one-line exception, assertion detail) and appends a
    │     Claude Haiku-generated plain-English RCA summary as a blockquote
    └─ gh pr create / gh pr comment              ← deterministic shell
          creates PR if none exists; comments assurance report on existing PR
    │
    ▼
[gate job]
    ├─ download-artifact (continue-on-error — absent when no story ID)
    └─ reads gate.json → exits 0 (green) or 1 (red)
          missing gate.json → exit 0 (no story → pass)
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

One skill is invoked in CI. The `prompt: "/test-generation"` field in `assurance.yml` is the entry point. Claude reads the skill file from the checked-out repo and follows its 8-step protocol:

1. Read the Jira story file (`${JIRA_DIR:-jira}/$STORY_ID.md`)
2. Resolve `DOMAIN.md` for ubiquitous language grounding
3. Run `build_context.py` → structured JSON (changed files, AST-level symbols, callers, diff excerpts)
4. Invoke the `test-writer` sub-agent with combined context
5. Run pytest against generated output
6. On failure: classify each failure as Locator bug / Implementation gap / Test infrastructure → write `generated/$STORY_ID/gate_notes.md` → stop. **No auto-heal. No re-runs.**
7. Write `generated/$STORY_ID/meta.json` (always, regardless of pass/fail — required by `append_record.py`)
8. Stop — downstream steps handle traceability

The skill enforces two hard constraints: never modify `src/domain/`, and write only to `generated/$STORY_ID/`.

> **Why no auto-heal?** Auto-heal consumed turns non-deterministically, masked real AC gaps (a broken implementation could pass after test adjustments), and made CI behaviour hard to reason about. Failures are now classified and surfaced cleanly so the developer understands what broke and why.

**Generated test conventions** (enforced from PROT-105 live-run learnings):
- `scenarios()` must reference `"{STORY_ID}.feature"` by filename — never a generic name
- HTTP tests: always use `httpx` (not `requests`); always read `BASE_URL = os.environ.get("BASE_URL", "http://localhost:3000")`
- Auth credentials must come from env vars with safe local defaults: `os.environ.get("TEST_BEARER_TOKEN", "valid-test-token")`
- Never hardcode URLs or tokens — CI injects real values; local runs fall back to defaults

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

## Workflow Environment Variables

Variables injected by `assurance.yml` into the agentic step and downstream scripts:

| Variable | Default | Set by | Purpose |
|----------|---------|--------|---------|
| `STORY_ID` | — | CI (required) | Jira story identifier, e.g. `PROT-105` |
| `JIRA_DIR` | `jira` | CI | Directory containing story markdown files; allows the workflow to point at a different fetch target |
| `BASE_URL` | `http://localhost:3000` | CI | Live server URL for HTTP tests; CI can override with real host |
| `TARGET_URL` | `http://localhost:3000` | CI | Alias for `BASE_URL` used by some test patterns |
| `TEST_BEARER_TOKEN` | `valid-test-token` | CI | Auth token for authenticated endpoint tests; real value injected from secrets |
| `JIRA_DATA_URL` | `https://shreynp.github.io/Assurance-CI` | CI | GitHub Pages base URL for `fetch_jira_ticket.py` |
| `DISPATCH_STORY_ID` | — | `workflow_dispatch` input | Overrides commit-message detection when set via manual trigger |
| `ANTHROPIC_API_KEY` | — | Secret (required) | API key for the `claude-code-action@v1` agentic loop and the `build_pr_body.py` RCA summary call |

---

## Scripts — `scripts/`

| Script | Called by | Purpose |
|--------|-----------|---------|
| `fetch_jira_ticket.py` | Workflow step | Fetches `PROT-NNN.md` from GitHub Pages (`JIRA_DATA_URL`) and writes it into `jira/` |
| `build_context.py` | Skill step 3 | Produces `/tmp/context.json` with changed files, symbols, callers, and diff excerpts |
| `append_record.py` | Workflow step | Appends a traceability record to `traceability/register.json` |
| `render_register.py` | Workflow step | Renders `register.json` → `REGISTER.md` markdown table |
| `resolve_gate.py` | Workflow step | Reads `register.json` and writes pass/fail decision to `/tmp/gate.json` |
| `build_pr_body.py` | Workflow step | Renders gate status, test results, RCA table, and AI-generated RCA summary into `/tmp/pr_body.md` for PR creation |
| `run_tests.py` | Workflow step (skill step 5) | Runs `pytest` against `generated/$STORY_ID/`, captures output and writes JSON report |

---

## PR Body Builder — `scripts/build_pr_body.py`

Produces `/tmp/pr_body.md` for `gh pr create` / `gh pr comment`. When `failed > 0` it adds a **Root Cause Analysis** section with two layers:

### 1. RCA table (static, no API cost)

Parsed from the pytest `--tb=short` output already stored in `{story_id}_report.json`:

| Column | Source |
|--------|--------|
| **Test** | `FAILED path - …` summary line, with `generated/STORY_ID/` prefix stripped |
| **Failure** | One-line exception message from the same summary line |
| **Detail** | First ≤3 `E ` assertion lines from the matching failure block, joined with ` · ` |

### 2. AI-generated summary (Claude Haiku)

After the table, a `> **Summary**: …` blockquote is rendered. `generate_worded_rca()` calls `claude-haiku-4-5-20251001` with the structured failure list and asks for a 2–3 sentence root cause summary focused on _why_ (not just _what_) failed, with an actionable recommendation.

- Requires `ANTHROPIC_API_KEY` in the `Build PR body` workflow step env
- Falls back silently (blockquote omitted) if the key is absent or the call fails — the table is always rendered

### Example PR output (failures present)

```markdown
### Root Cause Analysis

| Test | Failure | Detail |
|:-----|:--------|:-------|
| `test_export.py::test_csv_download` | `AssertionError: HTTP 404` | assert response.status_code == 200 |

> **Summary**: All three failures share a common root cause — the CSV export route
> is not registered in the Next.js app router, returning 404 for every request.
> Register the route handler at `app/api/export/route.ts` and re-run.
```

---

## Context Builder — `scripts/build_context.py`

Replaces the old raw `git diff HEAD~1 HEAD` dump (8 k cap, unstructured). Produces `/tmp/context.json`:

```json
{
  "changed_files": ["components/completeness-ring.tsx", "app/api/assessment/route.ts"],
  "changed_symbols": {
    "components/completeness-ring.tsx": ["CompletenessRingProps", "RADIUS", "CIRCUMFERENCE", "CompletenessRing"],
    "app/api/assessment/route.ts": ["GET", "POST"]
  },
  "callers": {
    "app/api/assessment/route.test.ts": ["route"]
  },
  "context_type": "both",
  "diff_excerpts": {
    "components/completeness-ring.tsx": "...targeted diff lines...",
    "app/api/assessment/route.ts": "...targeted diff lines..."
  }
}
```

`context_type` routes test strategy: `"ui"` → always Playwright; `"backend"` → pytest-bdd; `"both"` → both.

### Output schema

```json
{
  "changed_files": ["app/api/assessment/route.ts", "components/completeness-ring.tsx"],
  "changed_symbols": { "components/completeness-ring.tsx": ["CompletenessRing", "CompletenessRingProps"] },
  "symbol_signatures": {
    "components/completeness-ring.tsx": {
      "CompletenessRing": "export const CompletenessRing: React.FC<CompletenessRingProps> = ({ percentage, size = 120 })",
      "CompletenessRingProps": "export interface CompletenessRingProps { percentage: number; size?: number; }"
    }
  },
  "callers": { "app/assessment/page.tsx": ["completeness-ring"] },
  "context_type": "both",
  "diff_excerpts": { "components/completeness-ring.tsx": "...diff..." },
  "file_contents": { "app/api/assessment/route.ts": "...full source (≤200 lines)..." },
  "file_imports": { "components/completeness-ring.tsx": ["react", "@/lib/utils", "./types"] },
  "file_directives": { "components/completeness-ring.tsx": ["use client"] },
  "existing_tests": { "components/completeness-ring.test.tsx": "...content..." }
}
```

### Language support

The script uses two AST backends:

| Files | Parser | Symbols extracted |
|-------|--------|-------------------|
| `.py` | `ast` (stdlib) | Top-level `def`, `async def`, `class` at `col_offset == 0` |
| `.ts`, `.tsx`, `.js`, `.jsx` | `tree-sitter` + `tree-sitter-typescript` | Top-level `function_declaration`, `class_declaration`, `lexical_declaration`, `export_statement`, `interface_declaration`, `type_alias_declaration`, `enum_declaration` |

**`symbol_signatures`** — for each changed symbol, the full signature text up to (not including) the function body. For TypeScript this preserves type annotations and return types; for Python it includes parameter annotations and `->` return type. Interfaces and type aliases include their full body if ≤300 chars.

**`file_contents`** — full source text of changed files with ≤200 lines. Gives the model complete function bodies and surrounding context rather than only the `+` lines from the diff.

**`file_imports`** — import specifiers declared at the top of each changed file (`import_statement` nodes in TS, `ast.Import`/`ast.ImportFrom` in Python). Tells the test-writer which dependencies may need mocking.

**`file_directives`** — `'use client'` / `'use server'` directives extracted from the first non-import statements in each TS/TSX file. Determines the Next.js component type and therefore the test strategy: `'use client'` → Playwright DOM test; no directive or `'use server'` on a route → HTTP test.

**`existing_tests`** — co-located test files (`.test.ts`, `.spec.tsx`, `__tests__/`) for changed modules, plus all files from `generated/$STORY_ID/` when `--story-id` is passed. The test-writer extends these rather than generating from scratch.

**Caller detection** for TS/TSX files matches by file stem against `import_statement` string nodes (e.g. `from './completeness-ring'` → stem `completeness-ring`). Falls back to regex text scan if tree-sitter is unavailable. Scans `_TS_SEARCH_ROOTS` which covers the Next.js App Router layout:

```python
_TS_SEARCH_ROOTS = ("src", "app", "components", "lib", "hooks", "stores", "types", "utils", "pages", "features")
```

Python caller detection uses `_SEARCH_ROOTS = ("src", "scripts")`.

**`context_type` classifier** detects:
- `"ui"` — any path containing `dashboard`, `components`, or `app`
- `"backend"` — any path containing `domain`, `scripts`, `api`, or `lib`
- `"both"` — both signal types present

**`--story-id` flag** — when passed, `_find_existing_tests()` also scans `generated/<story-id>/` for previously generated `.feature`, `.py`, and `.ts` files so the agent can extend rather than regenerate.

**Dependencies**: `tree-sitter>=0.21.0` and `tree-sitter-typescript>=0.21.0` in `pyproject.toml`, installed via `pip install -e "assurance-ci/[dev]"`. If import fails, TS functions return empty gracefully — no crash.

---

## Cost Profile

| Approach | Model | Calls | Estimated cost/run |
|----------|-------|-------|--------------------|
| Old (fixed SDK calls) | Opus | 2 fixed | ~$0.50–1.00 |
| New (agentic loop) | Sonnet | 3–25 turns | ~$0.10–0.50 |

The agentic step runs with `max-turns: 25` and `continue-on-error: true`. If Claude hits the turn cap, the pipeline does not fail — it continues to append_record and PR comment so evidence is preserved. Failures inside the agentic loop are classified and written to `gate_notes.md`; no auto-healing is attempted.

---

## Jira File Format Contract

`jira/PROT-NNN.md` files are the source of truth for acceptance criteria. `src/domain/story_parser.py` extracts AC text using this pattern:

```
_AC_PATTERN = re.compile(r"^-\s+AC\d+:\s+(.+)$", re.MULTILINE)
```

**Every story file must have bullet-format AC lines immediately after `## Acceptance Criteria`:**

```markdown
## Acceptance Criteria

- AC1: Short machine-readable description of the criterion
- AC2: Another criterion
```

Prose-style bold headings (`**AC1 — Title**`) are for human readability and may coexist, but the parser ignores them. If no `- ACN:` bullets are present, `story_parser.py` raises `ValueError: No acceptance criteria found` and the CI run fails at the generate step.

When served via GitHub Pages, the URL is `https://shreynp.github.io/Assurance-CI/PROT-NNN.md` — fetched by `scripts/fetch_jira_ticket.py` using `JIRA_DATA_URL` env var.

---

## Local Usage

```bash
STORY_ID=PROT-101 claude
# then type: /test-generation
```

Claude picks up the same skill file, runs the identical 7-step loop with local tools. The Playwright MCP and context7 MCP are available locally too (via `.claude/mcp.json`).
