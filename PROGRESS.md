# Assurance CI — Progress

## Tier Declaration
- **Tier**: PROTOTYPE
- **Demo date**: 2026-06-23 (Monday)
- **One core flow that must be flawless**: Automated tests — generated tests run in CI, produce a real pass/fail execution report, and the gate resolves correctly.

## Stack
- **Primary language**: Python
- **Test runner**: pytest-bdd (API), Playwright Python (UI)
- **AI**: Anthropic Claude via `anthropic` SDK
- **Dashboard/Register viewer**: Streamlit (if UI needed)
- **CI**: GitHub Actions

## Session Log
- 2026-06-21: Proto-init — project scaffolded
- 2026-06-21: Proto-implement — 66 tests green; all SPEC features covered
- 2026-06-21: Proto-verify — all 66 tests green; dashboard verified at both viewports; 2 bugs fixed (register.json seeded from demo_records.json; CI workflow fallback SDK corrected openai→anthropic); VERIFIED
- 2026-06-22: Agentic guide v7 compliance — 116 tests green; added AGENTS.md, CLAUDE.md @import, .claude/agents/ (research-assistant, test-writer, docs-writer), .claude/skills/ship-it/, .claude/hooks.json + hook scripts, .claude/mcp.json, scripts/init.sh, feature_list.json, docs/adr/ (3 ADRs), docs/research/INDEX.md, .github/copilot-instructions.md, llms.txt, CONTRIBUTING.md, .agent-audit/, ruff in pyproject.toml

## What's built
| Feature | Status | Tests |
|---------|--------|-------|
| F1 — AI test generation | ✅ Scripts + generator domain module | 25 generator tests |
| F2 — Test execution | ✅ run_tests.py (bugs fixed) | 5 execution parsing tests |
| F3 — Traceability register | ✅ register.json + REGISTER.md + Streamlit dashboard | 6 register format tests |
| F4 — Story-keyed trigger | ✅ assurance.yml + commit_parser | 7 trigger tests |
| F5 — Deploy gate | ✅ resolve_gate.py | 8 gate tests |

## Demo script (2026-06-23)
**Open with the pain**: "Right now, when a developer ships assessment code, a QA manager has to read the PR, manually write test cases, run them, then paste results into a spreadsheet before an approver can sign off. That takes a day. Here's what happens instead."

1. Show the commit message: `PROT-101: add assessment submission endpoint`
2. Show the GitHub Actions run — the `assurance` job auto-triggers, calls Claude, runs the tests, writes the register row, resolves the gate
3. Open the dashboard → PROT-101 row shows GREEN, 4P/0F, linked SHAs
4. Click "Select run" → Execution Detail shows the actual test output (4 scenarios passed)
5. Switch story filter to PROT-102 → show the RED run (defect caught) and then the fixed GREEN run
6. Close: "The approver never needed to attend a meeting. The gate is the sign-off."

**Value Moment**: First time the approver reads the register instead of attending a meeting.

## How to run the dashboard
```bash
source .venv/bin/activate
streamlit run src/dashboard/app.py
```

## How to run the pipeline locally (dry run)
```bash
source .venv/bin/activate
git diff HEAD~1 HEAD > /tmp/test.diff

ANTHROPIC_API_KEY=sk-ant-... python scripts/generate_tests.py \
  --story-id PROT-101 --diff /tmp/test.diff --out generated/

python scripts/run_tests.py \
  --story-id PROT-101 --generated-dir generated/ --report-out traceability/reports/

python scripts/append_record.py \
  --story-id PROT-101 --commit-sha $(git rev-parse HEAD) --author $(git config user.email) \
  --generated-dir generated/ --report-dir traceability/reports/ --register traceability/register.json

python scripts/resolve_gate.py \
  --register traceability/register.json \
  --story-id PROT-101 --commit-sha $(git rev-parse HEAD) --output /tmp/gate.json
```
