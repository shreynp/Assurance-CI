# AGENTS.md
Role: Ultra-dense output. Sacrifice grammar for token efficiency. Preserve meaning. Omit pleasantries.

## Project
Assurance CI — story→gate traceability pipeline. Claude generates BDD tests from Jira story commits; tests run in CI; results appended to `traceability/register.json`; gate resolves red/green on PR.

## Stack
Python 3.12 · pytest-bdd (API) · Playwright Python (UI) · Anthropic SDK · GitHub Actions · virtualenv `.venv/`

## Commands
```bash
source .venv/bin/activate && pip install -e ".[dev]"
pytest tests/ -v                          # full suite
ruff check . && ruff format --check .    # lint
./scripts/init.sh                         # smoke test (run first each session)
python scripts/render_register.py         # regenerate REGISTER.md after seed changes
```

## Architecture Rules
- `src/domain/` pure: no I/O, no external calls — I/O only in `scripts/`
- Seed → `traceability/register.json` (never `_demo.json`); run `render_register.py` after
- Fix bugs in existing files — never create new files for a bug fix
- DOMAIN.md = source of truth for entity field names and ubiquitous language; read it before writing tests or new entities
- SPEC.md = acceptance criteria; don't deviate from AC without explicit user approval

## Skills — invoke these, don't re-implement them
| Trigger | Skill | Does |
|---------|-------|------|
| Generate/run tests for a story | `/test-generation` | Reads story, builds diff context, invokes `test-writer` agent, runs pytest, writes `meta.json` |
| Commit / ship completed work | `/ship-it` | Validates init.sh + tests + lint, stages, commits, optionally pushes |

## Agent Routing
| Task | Agent | Notes |
|------|-------|-------|
| Find files / grep symbols | `Explore` | Read-only; specify breadth: quick / medium / thorough |
| Plan 3+ step or multi-file task | `planner` | Required before implementation; produces file-level task list |
| Write tests for a story (CI or internal) | `test-writer` | CI mode when `STORY_ID` env set; internal mode otherwise |
| Update PROGRESS.md / REGISTER.md / ADRs | `docs-writer` | After code-reviewer approves |
| Vet new libraries before adding them | `research-assistant` | Batch multiple libs in ONE invocation; produces `docs/research/<lib>.md`; required before `pip install` |
| Post-implementation audit | `code-reviewer` | Multi-file or AC-touching changes only; skip for single-file edits; returns SHIP / ITERATE / BLOCK |
| Single-file trivial change | — | No subagent; act directly |

## Hooks (auto-fire — no action needed)
- **PostToolUse Write/Edit** → `format-file.sh` runs `ruff format` silently on `.py` files
- **PreCommit** → `pre-commit.sh` checks for secrets + domain purity violations; blocks commit on failure

## Testing
- New features: tests before marking done; verify with tool call output (not inference)
- BDD: `tests/features/` (Gherkin) · `tests/step_defs/` (steps) · `tests/test_*.py` (unit)
- Generated CI tests: `generated/$STORY_ID/` — `test-writer` agent owns this; `/test-generation` skill orchestrates

## Definition of Done
All gated by `/ship-it` skill — it enforces these mechanically:
1. `./scripts/init.sh` passes
2. `pytest tests/ -v` green (tool call evidence)
3. `ruff check .` passes
4. PROGRESS.md updated
5. No secrets in staged diff

## CI Behaviour (Claude Code Actions — headless, --max-turns 25)

**Turns are the scarce resource. Every exploratory or conversational turn reduces test output.**

### Autonomy
- Never pause for confirmation — decide, log it in one line, proceed
- File missing: create it with minimal structure; never ask
- Path ambiguous: pick the conventional interpretation; state it once
- Blocked after 2 attempts: emit `FAIL: <reason>` and stop; do not loop

### Turn Budget
- Batch all independent reads in one message — never sequential reads that could be parallel
- `grep` before `Read`: locate the exact line before opening a file
- Always pass `offset`+`limit` on files >150 lines — never read whole large files
- No orientation reads: only read a file if you will modify it or cite a specific line
- Combine existence check + read: `test -f foo && cat foo || echo MISSING` in one Bash call

### Scope
- Write only to `generated/$STORY_ID/` during test generation — never outside
- Read only source files named in the story AC or directly imported by the file under test
- Do not crawl the codebase for patterns; derive test structure from the AC and the specific file

### Output Format
- Prefix status lines: `PASS:`, `FAIL:`, `SKIP:`, `WRITE:` — one fact per line
- No prose narration between tool calls
- No trailing summary — the written files are the artifact

## Session Start
1. Read PROGRESS.md
2. `./scripts/init.sh` — fix before new work
3. Check `docs/adr/` before guessing at past decisions
4. Check `feature_list.json` for current feature state
