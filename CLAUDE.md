@import AGENTS.md

## Claude-Specific Behaviours

### Subagent Routing
- Use the `Explore` subagent for read-only codebase search
- Use the `planner` subagent before implementing tasks with 3+ steps or multi-file changes
- Run `code-reviewer` subagent after every implementation wave
- Spawn `research-assistant` (`.claude/agents/research-assistant.md`) before integrating any new library
- Do NOT spawn subagents for simple single-file changes

### Context Management
- Write to PROGRESS.md and `/compact` at natural session breakpoints
- Start fresh sessions for new features — `/clear` after each commit
- Check `docs/adr/` before guessing at past architectural decisions
- Use `feature_list.json` for feature state; use PROGRESS.md for narrative state

### Hallucination Prevention
- For any external library: verify on PyPI before suggesting install
- Use `context7` MCP server for version-specific API docs before writing integration code
- Pin exact library versions in all research queries
- For new dependencies, run `research-assistant` to produce a `docs/research/` note first
