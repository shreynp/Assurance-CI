# Assurance CI

Story → Commit → Generated Tests → Execution → Gate traceability pipeline for PROTECT AI.

## Triggering the workflow

**On push** — any commit to a PR branch fires the pipeline automatically via `pull_request: synchronize`. No special commit message needed; the story ID is detected from (in order): workflow dispatch input → commit message → PR title → branch name (e.g. `feat/PROT-105-...`).

**Manual dispatch via CLI:**
```bash
gh workflow run assurance.yml \
  --ref <branch> \
  --field story_id=PROT-105
```

**Manual dispatch via GitHub UI:** Actions → Assurance CI → Run workflow → select branch → enter story ID.

## How it works

1. A commit message containing a story ID (e.g. `PROT-101: add endpoint`) triggers the pipeline.
2. The story markdown is fetched from the `jira/` directory.
3. Claude generates a Gherkin feature file and a pytest-bdd or Playwright test script.
4. Tests are executed by pytest, targeting `BASE_URL` / `TARGET_URL` (default: `http://localhost:3000`).
5. Results are appended to `traceability/register.json`.
6. The gate job exits 0 (green / allow merge) or 1 (red / block merge).

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
| `build_pr_body.py` | `JIRA_DATA_URL` | *(optional)* | Renders ticket ID as hyperlink when set |

**Error behaviors:**
- Missing register → red gate (exits 1; not an exception)
- Missing acceptance criteria in story → `ValueError` from `load_story`
- Claude returning no text block → prints `ERROR:` message and exits 1
- Duplicate register records for same story+commit → last appended record wins

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
