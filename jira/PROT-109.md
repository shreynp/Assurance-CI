# PROT-109 — Show assessment history list on /history page

**Type**: Story  
**Priority**: Medium  
**Epic**: Assessment CRUD  
**Test type**: Playwright  

---

## User Story
As a market contributor, I want to see a chronological list of all my past assessment submissions on a dedicated history page, so that I can review what I scored for each element and task, and track my self-assessment record over time.

## Business Context
Currently a contributor can submit assessments but has no way to see what they submitted previously — the data disappears from view the moment they navigate away. Without a history view, contributors cannot self-audit, spot accidental duplicate submissions, or confirm that a recent PATCH (PROT-107) was applied correctly. The history page is the primary human-readable view of the `GET /api/assessments` endpoint (PROT-108) and is also the starting point for trend sparklines (PROT-111) and the CSV export (PROT-113).

---

## Description

Add a `/history` page to the Protect AI application. The page renders a table of all past assessment submissions for the logged-in user, fetched from `GET /api/assessments` (PROT-108) on page load. Rows are ordered most-recent-first (the API already returns them in this order).

### Table columns
| Column | Content |
|--------|---------|
| Element | The element name (e.g. "HCP Engagement") |
| Task | The task description string |
| Self Score | The `selfScore` rendered as a filled/empty star rating (★★★☆☆ for score 3) |
| Submitted | The `submittedAt` date formatted as a human-readable date (e.g. "23 Jun 2026 14:32") |

### Star rating rendering
- Score 1: ★☆☆☆☆
- Score 2: ★★☆☆☆
- Score 3: ★★★☆☆
- Score 4: ★★★★☆
- Score 5: ★★★★★

Filled stars (`★`) and empty stars (`☆`) must be visually distinguishable; do not rely on colour alone (accessibility).

### Empty state
When the user has no submissions, the table is replaced by a centred message: **"No assessments submitted yet."** A "Start your first assessment" link below the message navigates to `/assessment`.

---

## Acceptance Criteria

**AC1 — Page renders a table with four named columns**  
Given a user has at least one submission,  
When the `/history` page loads,  
Then a table is visible with column headers: "Element", "Task", "Self Score", and "Submitted".

**AC2 — Rows are ordered most-recent-first**  
Given a user has submissions at timestamps T1 < T2 < T3,  
When the `/history` table renders,  
Then the first row corresponds to T3 and the last row corresponds to T1.

**AC3 — Self Score column shows a star rating matching the numeric score**  
Given a submission with `selfScore: 3`,  
When its row renders in the table,  
Then the Self Score cell contains exactly 3 filled stars and 2 empty stars (e.g. "★★★☆☆").

**AC4 — Empty state message is shown when there are no submissions**  
Given the authenticated user has zero submissions,  
When the `/history` page loads,  
Then the table is not rendered and the text "No assessments submitted yet" is visible on the page.

**AC5 — Page is usable at 1280×800 without horizontal scrolling**  
Given a browser window set to 1280×800,  
When the `/history` page is loaded with at least 3 rows in the table,  
Then all four column headers and all cell content are visible without horizontal scrolling and the page body does not overflow the viewport width.

---

## Edge Cases

- **Single submission**: table renders with one row; no pagination controls shown.
- **Many submissions (50+)**: pagination controls appear if the UI paginates; or all records are rendered in a scrollable table with no UI overflow.
- **Very long task description**: cell should truncate with an ellipsis at a set max-width, not break the table layout.
- **Score of 1**: renders as "★☆☆☆☆" — verify this edge doesn't accidentally render as empty or zero stars.
- **`submittedAt` in a different timezone offset**: always display in the user's local timezone (browser default), not always UTC.

---

## Out of Scope
- Editing or deleting a submission from this page — see PROT-107.
- Sparkline charts — see PROT-111 (added on top of this page in a subsequent ticket).
- CSV export button — see PROT-113 (added on top of this page in a subsequent ticket).

## Dependencies
- PROT-108 (`GET /api/assessments`) is the data source; the page requires this endpoint to be available or mocked.
- PROT-101 (POST endpoint) is needed to have test fixture data for the table.

## Definition of Done
- [ ] `/history` page exists and renders the table
- [ ] Star rating component renders correctly for all scores 1–5
- [ ] Empty state tested with a dedicated Playwright scenario
- [ ] All 5 acceptance criteria pass as named Playwright scenarios
- [ ] The generated Gherkin feature file covers each AC as a distinct scenario
