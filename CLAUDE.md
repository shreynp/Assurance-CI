@import AGENTS.md
@import DOMAIN.md
@import SPEC.md

## Claude-Specific Behaviours

### Skill Invocations
- `/test-generation` — user says "generate tests", "run the assurance pipeline", or `STORY_ID` is in scope
- `/ship-it` — user says "ship", "commit", "push", "ready to commit"
- Never re-implement what a skill already does; invoke it

### Subagent Routing
- `Explore` for any codebase search before grep-guessing; specify breadth
- `planner` before implementing 3+ step or multi-file tasks — read its plan before touching code
- `code-reviewer` after multi-file or AC-touching changes only — skip for single-file trivial edits
- `research-assistant` before any new `pip install` — blocks hallucinated package names
- `docs-writer` after code-reviewer approves — updates PROGRESS.md, REGISTER.md, ADRs
- Skip subagents for single-file trivial changes

### Domain & Spec Grounding
- Read DOMAIN.md before writing tests, new entities, or Gherkin — use its ubiquitous-language terms verbatim
- Read SPEC.md to confirm scope; any AC deviation needs explicit user approval
- Assertions must use field names from DOMAIN.md entities (`story_id`, `commit_sha`, `gate_result`, etc.)

### Context Management
- Update PROGRESS.md at session end or before `/compact`
- `/clear` after each commit — fresh session per feature
- `feature_list.json` → feature state; PROGRESS.md → narrative state; `docs/adr/` → past decisions

### Hallucination Prevention
- External library: run `research-assistant` before suggesting any new dep — batch multiple libs in one invocation, don't spawn per-library
- **Context7 mandatory** — before writing any code that calls `anthropic` SDK, `pytest-bdd`, `playwright`, `httpx`, or `streamlit` APIs: resolve the library via context7 first. Non-negotiable. Wrong-version code → test failure → diagnosis → fix → retest is the most expensive loop in this project.
- GitHub Actions `pip install`: cross-check package names against actual SDK imports in source
