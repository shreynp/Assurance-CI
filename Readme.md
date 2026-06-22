# Assurance CI

Story → Commit → Generated Tests → Execution → Gate traceability pipeline for PROTECT AI.

## How it works

1. A commit message containing a story ID (e.g. `PROT-101: add endpoint`) triggers the pipeline.
2. The story markdown is fetched from the Jira data source.
3. Claude generates a Gherkin feature file and a pytest-bdd or Playwright test script.
4. Tests run against the Next.js dev server.
5. Results are appended to `traceability/register.json`.
6. The gate job exits 0 (green / allow merge) or 1 (red / block merge).

## Traceability dashboard

The traceability register is embedded into the PROTECT AI dashboard and deployed to Cloudflare on every push to `main`.

Live URL: https://protect.shreyas-jagannath.workers.dev/assurance

The `/assurance` route shows:
- KPI cards — total runs, green/red gates, stories covered
- Filterable register table — filter by story ID or gate status, click a row to inspect it
- Execution detail — story, commit SHA, gate verdict, file paths, full test output

## Local Streamlit viewer

To browse the register locally using the Streamlit dashboard:

```bash
cd /path/to/protect
.venv/bin/streamlit run assurance/src/dashboard/app.py
```

## CI secrets required

| Secret | Purpose |
|--------|---------|
| `ANTHROPIC_API_KEY` | Claude API — test generation |
| `GITHUB_TOKEN` | Auto-provided — PR comments and commits |

## Cloudflare deployment secrets

Set these in **GitHub → Settings → Secrets and variables → Actions**:

| Secret | Where to find it |
|--------|-----------------|
| `CLOUDFLARE_API_TOKEN` | Cloudflare dashboard → My Profile → API Tokens (Workers:Edit scope) |
| `CLOUDFLARE_ACCOUNT_ID` | Cloudflare dashboard → Workers & Pages sidebar, or `npx wrangler whoami` |

The `.github/workflows/deploy.yml` workflow deploys the full Next.js app (including the assurance dashboard) to Cloudflare Workers on every push to `main`.
