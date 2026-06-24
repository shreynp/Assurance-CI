# TODO — Assurance CI

## Known issues

- **PR auto-trigger suppressed by GITHUB_TOKEN** — GitHub does not fire `pull_request` events
  for PRs created by `GITHUB_TOKEN`. Pipeline auto-creates PRs using `GH_TOKEN: GITHUB_TOKEN`,
  so the assurance workflow doesn't re-trigger on subsequent pushes to that PR branch.
  **Permanent fix:** replace `secrets.GITHUB_TOKEN` in the `gh pr create` step with a dedicated
  PAT stored as `ACTIONS_PAT`. Documented in [docs/CI-ARCHITECTURE.md](docs/CI-ARCHITECTURE.md).

## Backlog

- **Flag stories with no coverage** — detect when `generated/<STORY_ID>/` is absent or
  `meta.json` records 0 scenarios, and surface a warning in the PR body / gate notes rather
  than silently passing.

- **Rename `scripts/` to `scripts-assurance-ci/`** — avoids collision when Assurance CI tooling
  is symlinked into a host repo (`protect-ai`) that already has its own `scripts/` directory.
  Requires updating all references in `assurance.yml`, `pyproject.toml`, and the skill files.

## Out of scope (by design)

- Hypothesis property-based tests — not in the accepted test stack (pytest-bdd + Playwright only)
- BrowserStack / TestRails integration — stretch goal from original brief; not pursued
