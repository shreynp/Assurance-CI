# PROT-119 — Add /admin page with summary table of assessments across all market contributors

**Type**: Story  
**Priority**: High  
**Epic**: Admin Panel  
**Test type**: Playwright  

---

## User Story
As a market administrator, I want a dashboard page that shows me how far each contributor in my market has progressed through the assessment framework, so that I can identify who needs follow-up, review individual scores at a glance, and report team-wide completion status to leadership.

## Business Context
Market administrators currently have no visibility into team assessment completion without asking each contributor individually. The admin dashboard provides a single-pane view of the entire team's progress. Sorted by least-progressed contributors at the bottom, it makes prioritising follow-up conversations immediately obvious. The expandable row detail (per-element scores) means an admin can drill into any contributor's record without needing a separate page navigation.

---

## Description

Add a `/admin` page accessible only to admin-role users (enforced separately by PROT-120). The page renders a summary table populated from `GET /api/admin/assessments` (PROT-118). Each row represents one contributor; the data is aggregated client-side from the raw submission list.

### Summary table columns
| Column | Content |
|--------|---------|
| Contributor | User's full name |
| Elements Scored | Count of distinct elements with at least one submission (0–5) |
| Average Self Score | Mean `selfScore` across all submissions for this contributor, to 1 decimal place |
| Last Submission | `submittedAt` date of the user's most recent submission, formatted "DD Mon YYYY" |

### Default sort
Rows are sorted by **Elements Scored descending** so the most-progressed contributors are at the top. Contributors who have not started (Elements Scored = 0) appear at the bottom.

### Expandable row detail
Clicking a contributor row expands an in-row detail panel showing that contributor's individual scores per element:

```
▼ Shreyas Jagannath               5    3.8    23 Jun 2026
    HCP Engagement        ★★★★☆  4
    Brand Planning         ★★★☆☆  3
    Campaign Execution    ★★★★★  5
    Patient Identification ★★★☆☆  3
    Media & Promotion      ★★★☆☆  3
```

The expanded detail shows the most recent `selfScore` per element (not the average). Clicking the row again collapses the detail.

---

## Acceptance Criteria

**AC1 — Page shows a summary table with the four required columns**  
Given an admin user with contributors in their market,  
When they navigate to `/admin`,  
Then a table is visible with column headers: "Contributor", "Elements Scored", "Average Self Score", "Last Submission".

**AC2 — Rows are sorted by Elements Scored descending**  
Given contributor A has scored 5 elements and contributor B has scored 2 elements,  
When the admin table renders,  
Then contributor A's row appears above contributor B's row.

**AC3 — Average Self Score is displayed to one decimal place**  
Given a contributor has scores [3, 4, 5] across their submissions (average = 4.0),  
When their row renders,  
Then the Average Self Score cell shows "4.0" — not "4", not "4.00".

**AC4 — Clicking a contributor row expands a detail panel with per-element scores**  
Given contributor "Shreyas Jagannath" has submissions for 3 elements,  
When the admin clicks on that row,  
Then a detail panel expands beneath the row showing the 3 scored elements and their most recent `selfScore` — the other 2 unscored elements are not shown.

**AC5 — Page is usable at 1280×800 viewport without horizontal scrolling**  
Given a browser window set to 1280×800,  
When the `/admin` page is loaded with at least 3 contributors in the table,  
Then all column headers and at least the first 3 rows are visible without horizontal scrolling and the page body does not overflow the viewport width.

---

## Edge Cases

- **Contributor with zero submissions**: row shows "0" for Elements Scored, "—" for Average Self Score and Last Submission (not 0 or empty string).
- **Single contributor in the market**: table renders with one row; no sort animation needed.
- **Two contributors with equal Elements Scored**: secondary sort by Contributor name ascending (alphabetical) as a tiebreaker.
- **Expanding multiple rows simultaneously**: only one row should be expanded at a time; expanding a second row collapses the first.
- **Admin is also a contributor**: the admin's own submissions appear in the table along with other contributors' rows.

---

## Out of Scope
- Editing or deleting a contributor's submissions from this page.
- Sending notifications or messages to contributors from this page.
- Multi-market admin view (admin sees only their own market).

## Dependencies
- PROT-118 (`GET /api/admin/assessments`) provides the raw submission data for this page.
- PROT-120 (role guard) must redirect non-admin users before this page renders.

## Definition of Done
- [ ] `/admin` page exists and renders the summary table
- [ ] Expandable row detail tested in Playwright (click to expand, click to collapse)
- [ ] Zero-submission contributor row renders "0" and "—" correctly
- [ ] All 5 acceptance criteria pass as named Playwright scenarios
- [ ] The generated Gherkin feature file covers each AC as a distinct scenario
