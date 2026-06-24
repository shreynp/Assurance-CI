# Extending Assurance-CI

This guide covers the four main extension points: adding a pipeline script, adding a context field, adding a Claude agent, and adding a skill.

---

## Adding a New Pipeline Script

Pipeline scripts live in `scripts/`. They communicate via JSON files — one script writes a file, the next reads it.

### Step 1 — Write the script

Follow the contract pattern:

```python
"""One-line purpose.

Inputs:
  ARG  --input-file  path to the JSON written by the previous step
  ENV  MY_VAR        (default: "value") — description

Outputs:
  FILE path/to/output.json — schema: {field: type}
  exit 0 — success
  exit 1 — unrecoverable error
"""
import argparse, json, sys
from pathlib import Path

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-file", required=True)
    args = parser.parse_args()
    # ... logic ...
    Path("output.json").write_text(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
```

### Step 2 — Add a step in `assurance.yml`

Insert the new step after the step that writes its input file:

```yaml
- name: My new step
  if: steps.story.outputs.has_story == 'true'
  run: |
    python assurance-ci/scripts/my_script.py \
      --input-file /tmp/previous_output.json \
      --output /tmp/my_output.json
  env:
    MY_VAR: some-value
```

### Step 3 — Add tests

Add a test class in `tests/test_error_paths.py` covering the failure modes (missing input file, malformed JSON, etc.).

---

## Adding a New Context Field

The context builder (`scripts/build_context.py`) produces `/tmp/context.json` for the test-generation skill. To add a new field:

1. Add a helper function in the appropriate section of `build_context.py` (the file has clear section dividers)
2. Call it in the `build()` function and add the result to the return dict:
   ```python
   def build(base, head, story_id=None):
       ...
       my_data = my_new_function(files)
       return {
           ...
           "my_new_field": my_data,
       }
   ```
3. Update the output schema in `build_context.py`'s module docstring
4. Add a test in `tests/test_build_context.py`
5. Update `docs/CI-ARCHITECTURE.md` (the context builder output schema section)

> **TypeScript / Next.js projects:** if your new field involves parsing TS/TSX/JS/JSX files, use the existing `_ts_parser()` / `changed_symbols_ts()` helpers in `build_context.py`. These require `tree-sitter>=0.21.0` and `tree-sitter-typescript>=0.21.0` — already in `pyproject.toml`. The helpers fail gracefully (return empty) if tree-sitter is unavailable, so Python-only paths are unaffected. See [ADR-004 Amendment 2](adr/ADR-004-claude-code-action-migration.md) for the full rationale.

---

## Adding a Claude Agent

Agents are sub-sessions with a focused system prompt and a narrow tool allowlist.

### File format (`.claude/agents/<name>.md`)

```markdown
---
name: my-agent
description: >
  One sentence describing what this agent does and when to invoke it.
  Be specific — this description is used by Claude to decide whether to
  spawn this agent or handle the task itself.
tools: Read, Write, Edit, Grep, Glob, Bash
model: sonnet
---
# Agent Name

## Purpose
...

## What to produce
...
```

### Registering the agent

The file being present in `.claude/agents/` is sufficient — Claude Code discovers agents automatically from that directory.

### Testing locally

```bash
# In a Claude session, type:
/my-agent
# or reference it in a skill prompt
```

---

## Adding a Skill

Skills are multi-step protocols invoked with `/<name>`. The main skill is `/test-generation`.

### File format (`.claude/skills/<name>/SKILL.md`)

```markdown
---
name: my-skill
description: >
  Trigger description — what situation this skill handles.
  Used for auto-trigger matching.
---
# My Skill

## Steps

### 1 — First step
Describe what Claude should do. Be precise — skills are followed literally.

### 2 — Second step
...
```

### Invoking from the workflow

To invoke your skill from `assurance.yml`, add a `claude-code-action@v1` step:

```yaml
- name: Run my skill
  uses: anthropics/claude-code-action@v1
  with:
    anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
    prompt: "/my-skill"
    claude_args: |
      --max-turns 25
      --model claude-sonnet-4-6
  env:
    MY_VAR: ${{ steps.story.outputs.story_id }}
```

### Invoking locally

```bash
# In any Claude Code session:
/my-skill
```

---

## Architecture Decisions

Before extending the pipeline in a significant way, read the ADRs — they document deliberate choices that should not be accidentally reversed:

| ADR | Decision | Key constraint |
|-----|----------|----------------|
| [ADR-001](adr/ADR-001-python-pytest-bdd.md) | Python + pytest-bdd as test stack | No switching to Jest/Vitest for server-side tests |
| [ADR-002](adr/ADR-002-domain-purity.md) | Domain layer purity | `src/domain/` must have zero I/O imports |
| [ADR-003](adr/ADR-003-register-json.md) | `register.json` as single source of truth | All gate logic reads from the register; no parallel truth stores |
| [ADR-004](adr/ADR-004-claude-code-action-migration.md) | `claude-code-action@v1` agentic loop | No auto-heal; `--max-turns 25`; tree-sitter for TS/TSX parsing |

---

## Data Contract Between Scripts

```
assurance.yml
    │
    ├─ fetch_jira_ticket.py    → jira/<id>.md
    ├─ build_context.py        → /tmp/context.json
    ├─ [claude-code-action]    → generated/<id>/meta.json
    │                            generated/<id>/<id>.feature
    │                            generated/<id>/test_<id>.py
    │                            generated/<id>/conftest.py
    ├─ run_tests.py            → traceability/reports/<id>_report.json
    ├─ append_record.py        → traceability/register.json (appended)
    ├─ render_register.py      → traceability/REGISTER.md
    ├─ resolve_gate.py         → /tmp/gate.json
    └─ build_pr_body.py        → /tmp/pr_body.md
```

Each script's module docstring documents its exact input files, output files, and exit codes.
