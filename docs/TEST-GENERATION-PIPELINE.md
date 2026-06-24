# Test Generation Pipeline — Detailed Reference

End-to-end walkthrough of how Assurance CI generates, runs, and gates tests for a JIRA story.

---

## Table of Contents

1. [Trigger & Story ID Extraction](#1-trigger--story-id-extraction)
2. [Environment Setup](#2-environment-setup)
3. [Generate and Validate Tests](#3-generate-and-validate-tests--the-core-step)
   - [3.1 Read the Story](#step-31--read-the-story)
   - [3.2 Resolve DOMAIN.md](#step-32--resolve-domainmd)
   - [3.3 Build Incremental Context](#step-33--build-incremental-context)
   - [3.4 Invoke the test-writer Agent](#step-34--invoke-the-test-writer-agent)
   - [3.5 Run Tests (inside Claude)](#step-35--run-tests-inside-claude)
   - [3.6 Report Failures and Stop](#step-36--report-failures-and-stop-no-self-heal)
   - [3.7 Write meta.json](#step-37--write-metajson)
4. [Independent Pytest Run](#4-run-generated-tests-independent-step)
5. [Append Traceability Record](#5-append-traceability-record)
6. [Gate Resolution](#6-gate-resolution)
7. [PR Creation & Gate Job](#7-pr-creation-artifact-upload--gate-job)
8. [End-to-End Data Flow](#end-to-end-data-flow)

---

## 1. Trigger & Story ID Extraction

The pipeline fires on any `pull_request` event or manual `workflow_dispatch`. Before any test work begins, the workflow extracts a story ID from four sources in priority order:

1. Manual dispatch input (`workflow_dispatch.inputs.story_id`)
2. Commit message
3. PR title
4. Branch name

It uses `commit_parser.extract_story_id()` to find a `PROT-NNN` pattern in each source. If nothing is found across all four, the entire pipeline skips with exit 0 — no story ID, no gate.

---

## 2. Environment Setup

Once a story ID is confirmed, the workflow:

1. Checks out the **target project** (the repo being tested) at `HEAD`
2. Checks out **Assurance CI** tooling at `assurance-ci/`
3. Installs Node 20 (for Next.js), Python 3.12, and all deps: `httpx`, `pytest`, `pytest-bdd`, `playwright`, `tree-sitter`, `tree-sitter-typescript`
4. **Exposes Assurance CI tooling** into the workspace:
   ```bash
   cp -r assurance-ci/.claude/. ./.claude/
   ln -s "$WORKSPACE/assurance-ci/scripts" scripts
   ```
   This is how Claude Code gets the `/test-generation` skill and `test-writer` agent.
5. **Overrides Claude permissions** to allow full `Bash(*)`, `Read(*)`, `Write(*)`, `Edit(*)`, `Glob(*)`, `Grep(*)` in CI (the default `settings.json` is narrower for local dev)
6. Fetches the Jira story markdown from GitHub Pages via `fetch_jira_ticket.py` → writes it to `assurance-ci/jira/$STORY_ID.md`
7. Starts the Next.js dev server (`nohup npm run dev`) and waits for it on port 3000 via `wait-on`

---

## 3. Generate and Validate Tests — The Core Step

```yaml
uses: anthropics/claude-code-action@v1
with:
  prompt: "/test-generation"
  claude_args: --max-turns 25 --model claude-sonnet-4-6
env:
  STORY_ID: PROT-NNN
  BASE_URL: http://localhost:3000
  JIRA_DIR: assurance-ci/jira
```

`claude-code-action` gives Claude Code a shell in the CI runner. Claude receives `/test-generation` as its first prompt and orchestrates the following steps autonomously using its tools (Bash, Read, Write, Edit, Grep, Glob).

The step has `continue-on-error: true` — even if Claude hits max turns or crashes, downstream steps always run.

---

### Step 3.1 — Read the Story

Claude runs:
```bash
cat assurance-ci/jira/$STORY_ID.md
```

Extracts: `title`, `description`, `acceptance_criteria[]`, and `test_type` (`pytest-bdd` or `playwright`, defaulting to `pytest-bdd` if absent).

---

### Step 3.2 — Resolve DOMAIN.md

```bash
test -f DOMAIN.md && echo "exists" || echo "missing"
```

- **Exists** → Claude reads the ubiquitous-language table and entity field definitions. These become hard constraints on Gherkin scenario names and step text — e.g., the agent must use `story_id`, `commit_sha`, `gate_result` verbatim rather than inventing its own terminology. Entity assertions must also use field names from DOMAIN.md.
- **Missing** → Generation continues without domain grounding; a warning is logged.

---

### Step 3.3 — Build Incremental Context

```bash
python scripts/build_context.py \
  --base HEAD~1 --head HEAD \
  --output /tmp/context.json \
  --story-id $STORY_ID
```

`build_context.py` does significant static analysis and produces `context.json`. This is what prevents Claude from hallucinating request/response shapes — it reads the actual implementation before writing assertions.

| Field | How it's built |
|-------|---------------|
| `changed_files` | `git diff --name-only HEAD~1 HEAD` |
| `changed_symbols` | Python: AST walk for top-level `FunctionDef`/`ClassDef` whose names appear in the diff. TS/TSX: tree-sitter parse, walk top-level declarations |
| `symbol_signatures` | Full function signature up to but not including the body, including TypeScript type annotations and return types |
| `callers` | Scans `src/`, `scripts/`, `app/`, `components/`, `lib/`, `hooks/`, etc. for files that import any changed module (1 level deep, both Python AST and tree-sitter for TS) |
| `context_type` | `"ui"` / `"backend"` / `"both"` — inferred from path patterns (`components/`, `app/`, `api/`, `domain/`, etc.) |
| `diff_excerpts` | `git diff HEAD~1 HEAD -- <file>` per changed file |
| `file_contents` | Full source text for any changed file ≤ 200 lines |
| `file_imports` | Import specifiers declared inside each changed file (what it depends on — useful for identifying what needs mocking) |
| `file_directives` | `'use client'` / `'use server'` per TS/TSX file — tells the agent whether a file is a React Client Component, Server Component, or API route |
| `existing_tests` | Co-located `.test.ts`, `.spec.tsx`, `__tests__/` files, plus previously generated tests from `generated/$STORY_ID/` |

The `context_type` field drives test strategy: `"ui"` forces Playwright even if `test_type` is unset; `"backend"` uses pytest-bdd; `"both"` uses whichever `test_type` the story specifies.

---

### Step 3.4 — Invoke the test-writer Agent

Claude invokes the `test-writer` sub-agent, passing the full combined payload: story ACs + DOMAIN context + the entire `context.json`. The agent is constrained to write to `generated/$STORY_ID/` only and must never touch `src/domain/`.

The agent produces three files:

#### `$STORY_ID.feature`

One Gherkin scenario per acceptance criterion. Scenario names use DOMAIN.md language verbatim. This is the AC source of truth and is never modified after generation — not during failure reporting, not during any downstream fix.

#### `conftest.py`

Always generated unconditionally. Contains:

- **`context` fixture** — a shared mutable `dict` passed between BDD steps, used as in-memory state across `given`/`when`/`then` calls.
- **`httpx_safe` autouse fixture** — wraps every `httpx` method (`get`, `post`, `put`, `patch`, `delete`, `request`) to catch `httpx.LocalProtocolError` and return a synthetic 400 response instead of crashing. This handles cases where the HTTP/1.1 stack rejects a malformed header before the request reaches the server — a protocol-layer rejection is still a valid rejection from the test's perspective.

```python
@pytest.fixture(autouse=True)
def httpx_safe(monkeypatch):
    for method in ("get", "post", "put", "patch", "delete", "request"):
        orig = getattr(httpx, method)
        def _safe(*args, orig=orig, **kwargs):
            try:
                return orig(*args, **kwargs)
            except httpx.LocalProtocolError:
                return _rejection_response()
        monkeypatch.setattr(httpx, method, _safe)
```

#### `test_$STORY_ID.py`

Step definitions with these invariants:
- `pytest-bdd` if `test_type == "pytest-bdd"` (or backend context); `playwright` if `context_type == "ui"` or `test_type == "playwright"`
- `scenarios("$STORY_ID.feature")` references the exact feature filename, never a glob
- `BASE_URL = os.environ.get("BASE_URL", "http://localhost:3000")`
- `TEST_BEARER_TOKEN = os.environ.get("TEST_BEARER_TOKEN", "valid-test-token")`
- The `context` fixture comes from `conftest.py` — never redefined in the test file
- No hardcoded URLs or secrets — CI injects real values; local runs fall back to defaults

---

### Step 3.5 — Run Tests (inside Claude)

```bash
pytest generated/$STORY_ID/ -v --tb=short
```

Claude observes the result. If all scenarios pass, it proceeds directly to writing `meta.json` and stops.

---

### Step 3.6 — Report Failures and Stop (no self-heal)

> Self-heal was removed. Claude reports and stops — it does not edit any file, does not re-run pytest.

If pytest exits non-zero, Claude reads every `FAILED`/`ERROR` line and classifies each failure:

| Class | Signature |
|-------|-----------|
| **Locator bug** | Wrong DOM selector, wrong ancestor, `Node is not an HTMLElement`, locator scoped to wrong parent |
| **Implementation gap** | `AssertionError` in test body, `data-testid` absent from DOM, count/state mismatch after fixtures ran cleanly |
| **Test infrastructure** | `ImportError`, `ModuleNotFoundError`, `StepNotImplementedError`, `scenarios()` `FileNotFoundError`, traceback in conftest fixture body |

Claude writes `generated/$STORY_ID/gate_notes.md`:

```markdown
# Gate Notes — PROT-NNN

## Test results

| Test | Result | Class | Evidence |
|------|--------|-------|----------|
| test_ac1_... | FAILED | Implementation gap | data-testid absent from DOM |

## Recommendation

Run `/assurance-resolve` to fix the identified issues and re-run assurance.
```

Then writes `meta.json` and stops. Remediation is handled separately by the `/assurance-resolve` skill.

---

### Step 3.7 — Write meta.json

Regardless of pass or fail, Claude writes:

```json
{
  "feature_file": "generated/PROT-NNN/PROT-NNN.feature",
  "test_script": "generated/PROT-NNN/test_PROT-NNN.py"
}
```

This is a hard requirement — `append_record.py` reads it unconditionally and raises `FileNotFoundError` if absent. Claude then stops.

---

## 4. Run Generated Tests (Independent Step)

This is a **separate, independent second pytest run** — distinct from what Claude did internally. It exists to produce an authoritative machine-readable report regardless of what happened inside Claude's context.

```python
result = subprocess.run(
    ["pytest", f"generated/{story_id}", "--tb=short", "-v", "--no-header"],
    capture_output=True, text=True,
)
passed = int(m.group(1)) if (m := re.search(r"(\d+) passed", output)) else 0
failed = int(m.group(1)) if (m := re.search(r"(\d+) failed", output)) else 0
```

Writes `traceability/reports/$STORY_ID_report.json`:

```json
{
  "story_id": "PROT-NNN",
  "commit_sha": "abc123...",
  "author": "github-actor",
  "passed": 3,
  "failed": 1,
  "environment": "Linux",
  "timestamp": "2026-06-24T10:00:00+00:00",
  "output": "...",
  "exit_code": 1
}
```

Also `continue-on-error: true`. The pipeline always continues to the record/gate steps.

---

## 5. Append Traceability Record

`append_record.py` reads both `meta.json` (written by Claude) and the JSON report (written by the independent pytest run), constructs a `TraceabilityRecord`, and appends it to `traceability/register.json`.

The `GateResult` is derived from `ExecutionReport.all_passed`:

```python
@property
def all_passed(self) -> bool:
    return self.failed == 0 and self.passed > 0
```

The `passed > 0` check is deliberate — **zero passed with zero failed is treated as red**. An empty run (e.g., no tests collected, broken conftest) cannot count as evidence of passing. This is the fail-closed invariant.

A `TraceabilityRecord` contains: `story_id`, `commit_sha`, `author`, `feature_file_path`, `test_script_path`, `execution_report`, `gate_result`, `appended_at`.

---

## 6. Gate Resolution

`resolve_gate.py` reads `traceability/register.json`, filters for records matching `story_id + commit_sha`, takes the last (most recently appended) record, and writes `/tmp/gate.json`:

```json
{ "status": "green", "reason": "All 3 scenario(s) passed" }
```
or
```json
{ "status": "red", "reason": "2 scenario(s) failed out of 3" }
```

Fail-closed edge cases — all resolve to red:

| Condition | Reason |
|-----------|--------|
| Register file not found | `"Register not found — no test evidence"` |
| No matching record for story + commit | `"No record found for PROT-NNN @ abc1234"` |
| Register contains invalid JSON | Script exits 1 |
| `passed == 0 and failed == 0` | `all_passed` is `False` — empty run is not evidence |

---

## 7. PR Creation, Artifact Upload & Gate Job

`build_pr_body.py` formats a markdown assurance report from the gate result and test output. The workflow creates a new PR or adds a comment to an existing one for the branch.

The gate result is uploaded as a GitHub Actions artifact (`gate-result`). The separate `gate` job (with `needs: assurance`) downloads it and enforces the final decision:

```python
gate = json.load(open("/tmp/gate.json"))
sys.exit(0 if gate["status"] == "green" else 1)
```

Exit 1 blocks the merge. This job always runs even when `assurance` steps failed with `continue-on-error`, ensuring the gate is never silently bypassed. If the artifact is absent (no story ID was found), the gate passes — no story, no gate obligation.

---

## End-to-End Data Flow

```
Commit / PR
    │
    ▼
Extract story ID
(commit message → PR title → branch → dispatch)
    │
    ├─ no story ID found → skip, exit 0
    │
    ▼
Fetch JIRA story markdown (GitHub Pages → assurance-ci/jira/$STORY_ID.md)
    │
    ▼
Install deps, expose .claude/ tooling, start Next.js dev server
    │
    ▼
claude-code-action runs /test-generation  [continue-on-error: true]
    │
    ├─ build_context.py → /tmp/context.json
    │    changed_files, changed_symbols, symbol_signatures,
    │    callers, diff_excerpts, file_contents,
    │    file_imports, file_directives, existing_tests
    │
    ├─ test-writer agent writes:
    │    generated/$STORY_ID/$STORY_ID.feature   (Gherkin, 1 scenario per AC)
    │    generated/$STORY_ID/conftest.py          (context fixture + httpx_safe)
    │    generated/$STORY_ID/test_$STORY_ID.py   (pytest-bdd or Playwright)
    │
    ├─ pytest run #1 (internal to Claude)
    │    pass → write meta.json, stop
    │    fail → classify failures, write gate_notes.md, write meta.json, stop
    │
    └─ (continue-on-error: true — pipeline always continues)
    │
    ▼
pytest run #2 (independent workflow step)  [continue-on-error: true]
    └─ → traceability/reports/$STORY_ID_report.json
         (passed, failed, output, exit_code)
    │
    ▼
append_record.py
    └─ reads meta.json + report
       → TraceabilityRecord appended to traceability/register.json
         (gate = green only if passed > 0 AND failed == 0)
    │
    ▼
render_register.py → REGISTER.md (human-readable)
    │
    ▼
git commit & push
(traceability/ + generated/ → branch)
    │
    ▼
resolve_gate.py
    └─ reads register → /tmp/gate.json (green / red)
       fail-closed: missing register, missing record, empty run → red
    │
    ▼
build_pr_body.py → PR comment with assurance report
    │
    ▼
gate job (separate, needs: assurance)
    └─ downloads gate-result artifact
       exit 0 → green, merge allowed
       exit 1 → red, merge blocked
       artifact absent → no story ID, gate passes
```
