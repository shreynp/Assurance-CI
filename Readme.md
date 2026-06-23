# Assurance CI

Story → Commit → Generated Tests → Execution → Gate traceability pipeline for PROTECT AI.

## Triggering the workflow

**Manual dispatch via CLI (preferred):**
```bash
gh workflow run assurance.yml \
  --repo shreynp/protect-ai \
  --ref feat/PROT-105-<slug> \
  --field story_id=PROT-105
```

**Manual dispatch via GitHub UI:** Actions → Assurance CI → Run workflow → select branch → enter story ID.

**Push to a PR branch (fallback)** — fires automatically via the `pull_request` event. The story ID is detected from (in order): workflow dispatch input → commit message → PR title → branch name. Note: GitHub suppresses `pull_request` events for PRs auto-created by `GITHUB_TOKEN`; use manual dispatch in that case. See [CI-ARCHITECTURE.md](docs/CI-ARCHITECTURE.md) for the known limitation and permanent fix.

**Commit message format:** `feat(PROT-NNN): <story title>` — the ticket ID must appear in the commit message for the pipeline to detect the story.

## How it works

1. The story ID is resolved (dispatch input → commit message → PR title → branch name).
2. The story markdown is fetched from `jira/PROT-NNN.md`.
3. Claude generates a Gherkin feature file (`generated/<ID>/<ID>.feature`) and a pytest-bdd or Playwright test script (`generated/<ID>/test_<id>.py`).
4. Tests run via pytest against `BASE_URL` / `TARGET_URL` (default: `http://localhost:3000`).
5. Results are appended to `traceability/register.json` and committed back to the branch.
6. The gate job exits 0 (green / allow merge) or 1 (red / block merge).

**If the gate is red:** run `/assurance-resolve PROT-NNN` in Claude Code on the protect repo — it pulls the CI-committed artifacts, diagnoses failing scenarios, and guides fixing only what failed.

## Traceability dashboard

The traceability register can be browsed locally using the Streamlit dashboard.

The dashboard shows:
- KPI cards — total runs, green/red gates, stories covered
- Filterable register table — filter by story ID or gate status, click a row to inspect it
- Execution detail — story, commit SHA, gate verdict, file paths, full test output

## Local Streamlit viewer

To browse the register locally:

```bash
.venv/bin/streamlit run src/dashboard/app.py
```

## Script pipeline contracts

The pipeline scripts hand off data through intermediate files:

```
generate_tests.py  ──►  <out>/<story-id>/meta.json          (feature_file, test_script paths)
run_tests.py       ──►  <report-dir>/<story-id>_report.json  (passed, failed, output)
append_record.py   ──►  traceability/register.json           (full traceability record)
resolve_gate.py    ──►  gate.json                            (status: green | red)
```

**Env vars consumed by the pipeline:**

| Script | Variable | Default | Purpose |
|--------|----------|---------|---------|
| `generate_tests.py` | `ANTHROPIC_API_KEY` | *(required)* | Claude API — test generation |
| `run_tests.py` | `GITHUB_SHA` | `local` | Commit SHA recorded in report |
| `run_tests.py` | `GITHUB_ACTOR` | `$USER` | Author recorded in report |
| `run_tests.py` | `RUNNER_OS` | `local` | Environment string |
| `run_tests.py` | `TEST_BEARER_TOKEN` | `valid-test-token` | Auth token for authenticated endpoint tests; CI injects the real value from secrets |
| `build_pr_body.py` | `JIRA_DATA_URL` | *(optional)* | Renders ticket ID as hyperlink when set |

**Error behaviors:**
- Missing register → red gate (exits 1; not an exception)
- Missing acceptance criteria in story → `ValueError` from `load_story`
- Claude returning no text block → prints `ERROR:` message and exits 1
- Duplicate register records for same story+commit → last appended record wins
- Zero tests collected (0 passed, 0 failed) → red gate — an empty run is not evidence of passing

## CI secrets required

| Secret | Purpose |
|--------|---------|
| `ANTHROPIC_API_KEY` | Claude API — test generation |
| `GITHUB_TOKEN` | Auto-provided — PR comments and commits |

## GitHub App prerequisite

`claude-code-action@v1` authenticates via OIDC token exchange through the **Claude Code GitHub App**. The app must be installed on the target repository or the action fails with:

```
App token exchange failed: 401 Unauthorized - Claude Code is not installed on this repository.
```

Install it at **https://github.com/apps/claude** and grant access to the target repo before running the workflow.
