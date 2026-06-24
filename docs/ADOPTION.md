# Adopting Assurance-CI in a New Project

This guide walks you through wiring Assurance-CI into a project other than `protect-ai`.

---

## 1. Fork the Repo

Fork `shreynp/Assurance-CI` or copy the directory structure into your own repo. The pipeline lives entirely in `.github/workflows/assurance.yml` and the `scripts/` and `.claude/` directories.

---

## 2. Publish Your Jira Stories as Static Files

Assurance-CI fetches story markdown over HTTP. The simplest approach is GitHub Pages:

1. Create a `jira/` directory at the root of your Assurance-CI fork
2. Add story files as `jira/PROJ-NNN.md` using this format:

```markdown
# PROJ-101 — Short story title

**Test type**: pytest-bdd

## Description
One or two sentences describing what the feature does.

## Acceptance Criteria

- AC1: Short machine-readable criterion
- AC2: Another criterion
```

3. Enable GitHub Pages for your fork (Settings → Pages → Deploy from branch `main`, folder `/jira`)
4. Set `JIRA_DATA_URL` in `assurance.yml` to your Pages base URL:
   ```yaml
   JIRA_DATA_URL: https://<your-org>.github.io/<your-assurance-repo>
   ```

---

## 3. Point the Pipeline at Your App

In `assurance.yml`, update the dev server URL and the story ID pattern:

```yaml
# Replace with how your app starts
- name: Start dev server
  run: nohup npm run dev > /tmp/dev.log 2>&1 &

# Replace with your app's local URL
env:
  BASE_URL: http://localhost:3000
  TARGET_URL: http://localhost:3000
```

If your story IDs use a different prefix (e.g. `MYPROJ-` instead of `PROT-`), update `src/domain/commit_parser.py`:
```python
_STORY_ID_RE = re.compile(r"\b(MYPROJ-\d+)\b")
```

---

## 4. Enable the Required GitHub Action

The core generation step uses [`anthropics/claude-code-action@v1`](https://github.com/anthropics/claude-code-action). No separate install is needed — `assurance.yml` references it directly. Ensure your fork's GitHub Actions settings allow third-party actions (Settings → Actions → General → Allow all actions, or add `anthropics/*` to the allowed list).

---

## 5. Install Python Dependencies

The pipeline requires `tree-sitter` and `tree-sitter-typescript` for TS/TSX/JS/JSX AST analysis in `build_context.py`. These are already in `pyproject.toml` under `[project.optional-dependencies] dev` — the CI workflow installs them via:

```bash
pip install -e "assurance-ci/[dev]"
```

If you are not using `pyproject.toml`, install directly:

```bash
pip install tree-sitter>=0.21.0 tree-sitter-typescript>=0.21.0 \
  httpx pytest pytest-bdd playwright pytest-playwright \
  anthropic python-dotenv pydantic
```

Without `tree-sitter`, `build_context.py` falls back gracefully (empty symbols for TS files) but test generation will lack the symbol context that grounds Claude's assertions.

---

## 6. Review Claude Permissions (`.claude/settings.json`)

The `assurance.yml` workflow overrides `.claude/settings.json` at runtime to allow full tool access inside the CI runner:

```json
{
  "permissions": {
    "allow": ["Bash(*)", "Read(*)", "Write(*)", "Edit(*)", "Glob(*)", "Grep(*)"],
    "deny": []
  }
}
```

For local development, the checked-in `settings.json` uses a narrower allowlist (specific `Bash(python scripts/*)`, `Bash(pytest *)` etc.) to prevent runaway tool use. If you need to tighten or customise permissions for your project, edit `.claude/settings.json` — the CI override will still apply during Actions runs.

The `PostToolUse[Write]` hook (`.claude/hooks/format-file.sh`) auto-runs `ruff format` on every `.py` file Claude writes. If your project uses a different Python formatter, update this hook script.

---

## 7. Add the Required Secret

In your GitHub repo settings (Settings → Secrets → Actions), add:

| Secret | Value |
|--------|-------|
| `ANTHROPIC_API_KEY` | Your Anthropic API key |

`GITHUB_TOKEN` is auto-provided by GitHub Actions — no action needed.

---

## 8. Update the Assurance-CI Checkout

In `assurance.yml`, the pipeline checks out Assurance-CI by repository name. Update this to your fork:

```yaml
- name: Checkout Assurance CI tooling
  uses: actions/checkout@v5
  with:
    repository: <your-org>/<your-assurance-repo>  # ← update this
    path: assurance-ci
```

---

## 9. Smoke-Test with a Manual Dispatch

Run the pipeline against a known story to verify the setup:

```bash
gh workflow run assurance.yml --ref main --field story_id=PROJ-101
```

Watch the run in the Actions UI. Common first-run issues:
- **"Story not found"** — check that `JIRA_DATA_URL` is correct and the `jira/*.md` file is published
- **"Dev server not ready"** — increase the `wait-on` timeout or check your start command
- **No tests generated** — check `STORY_ID` is set and the story has `- ACN:` bullets under `## Acceptance Criteria`

See [docs/TROUBLESHOOTING.md](TROUBLESHOOTING.md) for more.
