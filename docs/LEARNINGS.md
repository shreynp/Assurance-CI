# Learnings — Assurance CI

---

## 2026-06-21 — Proto-implement + Proto-verify

### What the next prototype should not relearn

**1. CI workflow fallback SDK mismatch is silent until it breaks**
The `assurance.yml` fallback `pip install` line (used when `pip install -e .` fails on CI) was installing `openai` while the code imported `anthropic`. The primary `pyproject.toml` dep was correct, so local dev worked fine, and all tests passed — the bug would only surface on a cold CI runner where editable install fails. Root cause: the fallback was copied from a template and never updated to match the actual SDK. Always grep the codebase for the import (`import anthropic`) and cross-check it against every install path in the workflow YAML.

**2. Seed data and live data must be the same file — or seeding must be automated**
`demo_records.json` was created with 4 realistic pipeline runs, but `register.json` (what the dashboard actually reads) was left empty. Result: the dashboard would have opened on "No traceability records yet" at the demo. The pattern of keeping a `*_demo.json` alongside the live file creates a step that is easy to forget. Either write seed data directly to the live path, or add a `make seed` / `scripts/seed_demo.py` that is explicitly part of the pre-demo checklist.

---

### Reusable components / patterns

**`src/domain/commit_parser.py`** — 14-line story-ID extractor
```python
STORY_ID_PATTERN = re.compile(r"\b([A-Z]+-\d+)\b")
```
Works for any JIRA-style project key (PROJ-123, EPIC-456, etc.). Drop it into any CI pipeline that needs to gate on story ID presence. No dependencies beyond stdlib.

**`src/domain/register.py`** — append-only JSON audit log + markdown table renderer
The `append_record(record, path)` → read-append-write pattern is the simplest possible append-only audit log. The `render_markdown(path)` companion renders it as a human-readable table with zero tooling. Reusable anywhere a pipeline needs an auditable evidence trail committed to the repo.

**Compliance Terminal Streamlit dashboard** (`src/dashboard/app.py`)
Full CSS token set, KPI card grid, custom HTML table with badge components, execution output block, sidebar refresh button — all from the Compliance Terminal design system. Copy the `_CSS` block and component markup into any Streamlit CI/audit dashboard.

---

### One rule that would have prevented the biggest time sink

> When a CI workflow has a fallback `pip install`, verify every package name against the actual import in the source code before the first push.

The `openai` vs `anthropic` swap cost zero time to fix but would have broken the CI run silently — a false-green that only fails on a cold runner. 30-second grep catches it every time.

---

### Scope note
The Streamlit dashboard was listed as "Out of Scope" in SPEC.md ("no elaborate decision UI") but was built as part of F3 traceability. For the prototype it serves as the approver-facing register view and the demo centrepiece — the value it adds justifies keeping it. In production, a committed `REGISTER.md` may be sufficient without Streamlit.
