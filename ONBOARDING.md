# Onboarding Guide

Assurance-CI is a GitHub Actions pipeline that converts a Jira story into BDD/Playwright tests, runs them against your app's dev server, and gates PRs on the result. Every run produces a traceable record in `traceability/register.json`.

---

## Prerequisites

- Python 3.12+
- Node 20+
- An `ANTHROPIC_API_KEY` with access to Claude Sonnet

---

## Local Setup (5 commands)

```bash
# 1. Clone and enter the repo
git clone https://github.com/shreynp/Assurance-CI && cd Assurance-CI

# 2. Install Python dependencies
pip install -e ".[dev]"

# 3. Install Playwright browser
playwright install chromium --with-deps

# 4. Run the test suite to verify your setup
pytest tests/ -q

# 5. (Optional) Launch the traceability dashboard
streamlit run src/dashboard/app.py
```

---

## Triggering the Pipeline on a PR

The pipeline auto-detects a story ID from your commit message, PR title, or branch name using the pattern `PROT-NNN`.

**Automatic trigger (recommended):** commit with a story ID in the message:
```bash
git commit -m "PROT-101: add assessment submission endpoint"
```

**Manual trigger (useful for testing):**
```bash
gh workflow run assurance.yml --ref <branch> --field story_id=PROT-101
```

---

## What the Pipeline Does

1. Extracts the story ID from your commit
2. Fetches the Jira story markdown from GitHub Pages
3. Starts your app's dev server
4. Runs the `/test-generation` Claude skill to write and run tests
5. Appends a traceability record to `traceability/register.json`
6. Posts a gate report comment on the PR
7. The gate job exits 0 (green) or 1 (red, blocks merge)

---

## Where to Go Next

| Document | Contents |
|----------|---------|
| [docs/CI-ARCHITECTURE.md](docs/CI-ARCHITECTURE.md) | Full pipeline architecture, MCPs, agents, context builder |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Code patterns, domain purity rules, testing approach |
| [docs/ADOPTION.md](docs/ADOPTION.md) | How to use this pipeline in a different project |
| [docs/EXTENDING.md](docs/EXTENDING.md) | How to add new scripts, agents, or skills |
| [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) | Common failure modes and how to diagnose them |
