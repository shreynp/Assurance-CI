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
- 2026-06-23: claude-code-action@v1 migration — 142 tests green; Phase 1–4 of PLAN.md complete: scripts/build_context.py (18 tests), .claude/settings.json (allowlists + PostToolUse hook), .claude/skills/test-generation/SKILL.md (agentic orchestration skill), generator.py context dict params (36 tests), assurance.yml rewritten to use anthropics/claude-code-action@v1 (single step replaces get-diff + generate + run)
- 2026-06-23: CI debugging chain (5 fixes) — (1) removed push trigger from assurance.yml (claude-code-action@v1 only supports PR/issue-comment events); (2) bumped all actions to Node.js 24-compatible versions (checkout@v5, setup-python@v6, artifact@v5); (3) replaced head_commit context (push-only) with git log + PR_TITLE fallback; (4) fixed protect-ai workflow to clone Assurance-CI into assurance-ci/ and run scripts from there; (5) bulk-added parseable `- ACN:` bullet lines to all 22 jira files (parser requires this format, files only had bold `**ACN — Title**` prose headings)
- 2026-06-23: PROT-105 learnings backport — 10 improvements from the live protect-ai run: (1) workflow_dispatch trigger + optional story_id input; (2) permissions: contents: write + pull-requests: write; (3) fetch-depth: 0 + token on checkout; (4) DISPATCH_STORY_ID override in story extraction; (5) Fetch Jira ticket step from GitHub Pages; (6) BASE_URL + TARGET_URL + JIRA_DIR env vars passed to claude-code-action; (7) [skip ci] on traceability commit; (8) continue-on-error on gate write + artifact download; (9) Build PR body + Create/update PR steps wired in; (10) test-generation skill: JIRA_DIR env var, httpx convention, env-var auth tokens, scenarios("{STORY_ID}.feature") naming rule
- 2026-06-23: Agentic step hardening — three final changes synced from protect-ai live run: (1) test-generation skill removes auto-heal loop entirely — skill now reports failures and stops (Category A/B classification retained in comments but no fixing attempted); rationale: auto-heal consumed turns non-deterministically, masked real AC gaps, and made CI behaviour hard to explain; (2) assurance.yml agentic step set to max-turns 25 (up from default 10) to give Claude enough headroom for multi-file test generation without hitting the cap; (3) continue-on-error: true added to the agentic step so the pipeline always reaches append_record / PR comment even if Claude exits at max turns — failure evidence is preserved rather than swallowed
- 2026-06-24: TS/TSX AST support in build_context.py — root cause: build_context.py was Python-only for AST parsing; all TS/TSX/JS/JSX changed files produced empty changed_symbols, callers, and diff_excerpts. Confirmed via PROT-112 run #28041461751 (7 changed files, all TS/TSX, zero context). Fix: added full tree-sitter TS/TSX/JS/JSX support — _ts_parser(), _ts_decl_name(), changed_symbols_ts(), find_ts_callers() — plus tree-sitter and tree-sitter-typescript to pyproject.toml. Also widened context_type classifier to recognise components/, app/, api/, lib/ path segments. Verified against PROT-112 commit range: 10 changed symbols, import-based callers, and diff excerpts now produced for all TS files.

## What's built
| Feature | Status | Tests |
|---------|--------|-------|
| F1 — AI test generation | ✅ Scripts + generator domain module + context dict path | 36 generator tests |
| F2 — Test execution | ✅ run_tests.py (bugs fixed) | 5 execution parsing tests |
| F3 — Traceability register | ✅ register.json + REGISTER.md + Streamlit dashboard | 6 register format tests |
| F4 — Story-keyed trigger | ✅ assurance.yml + commit_parser | 7 trigger tests |
| F5 — Deploy gate | ✅ resolve_gate.py | 8 gate tests |
| F6 — Agentic CI loop | ✅ claude-code-action@v1 + /test-generation skill + build_context.py | 18 context tests |

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
