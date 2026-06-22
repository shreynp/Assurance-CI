---
name: ship-it
description: >
  Release pipeline skill. Use when committing completed work — "ship it", "commit",
  "push", "ship this", "ready to commit". Runs validation gate (init.sh + tests + lint),
  stages files, writes descriptive commit, and optionally pushes. Always confirms
  before destructive operations.
---
# Ship-It Skill

## Pipeline (run in order — stop on failure)

1. **Pre-flight** — `./scripts/init.sh` must pass
2. **Tests** — `pytest tests/ -v --tb=short` must be green
3. **Lint** — `ruff check .` must pass (fix with `ruff check . --fix` if minor)
4. **Inspect** — `git diff --staged` then `git status` — show user what will be committed
5. **Confirm** — ask user to approve the file list before staging
6. **Commit** — `git add [specific files]` then commit with descriptive message
7. **Push** (only if explicitly asked) — `git push` after explicit confirmation

## Commit Message Format
```
[type]: [description]

[optional body with more detail]

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
```
Types: `feat` / `fix` / `docs` / `test` / `chore` / `ci`

## Hard Rules
- NEVER commit `.env` or any file matching secret patterns (`sk-ant-`, `API_KEY=`, `password =`)
- NEVER force push to `main`
- NEVER commit without green test output from an actual tool call
- NEVER push without explicit user confirmation in this session
- Stage specific files by name — never `git add -A` blindly

## Definition of Done Gate
All must be true before generating the commit:
- [ ] `./scripts/init.sh` passed (tool call evidence)
- [ ] `pytest tests/ -v` passed (tool call evidence)
- [ ] `ruff check .` passed (tool call evidence)
- [ ] PROGRESS.md updated with what was done
- [ ] No secrets in staged diff (confirmed by grep)
