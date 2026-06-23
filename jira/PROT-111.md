# PROT-111 — Show self-score trend sparkline per element on /history

**Type**: Story  
**Priority**: Low  
**Epic**: Analytics  
**Test type**: Playwright  

---

## User Story
As a market contributor reviewing my assessment history, I want to see a small trend chart next to each element showing how my self-score has changed across submissions, so that I can immediately spot whether my confidence in an element is improving, declining, or stalling — without manually scanning dates and scores across rows.

## Business Context
The `/history` page (PROT-109) shows a flat table of individual submission rows. If a contributor has scored "Campaign Execution" five times, they have to manually compare five rows to understand whether they are improving. A sparkline — a tiny inline chart showing the score trajectory — communicates that trend in under a second. This is a pure analytics enhancement on top of the existing history data; it requires no new API endpoints.

---

## Description

On the `/history` page, group submissions by element and add a sparkline chart to the right of each unique element's row group header. The sparkline plots one data point per submission for that element, ordered chronologically left to right on the x-axis.

### Grouping model
Rather than a flat list of submission rows (from PROT-109), the history page is updated to a grouped-by-element layout:

```
HCP Engagement   ▁▃▅▇   [3 submissions]
  ├─ Task A   ★★★★☆   23 Jun 2026
  ├─ Task A   ★★★☆☆   10 Jun 2026
  └─ Task A   ★★☆☆☆   01 Jun 2026

Brand Planning   ▅        [1 submission]
  └─ Task B   ★★★★☆   20 Jun 2026
```

The sparkline lives in the element group header row, not in individual submission rows.

### Sparkline colour logic
- Trend direction is determined by comparing the most recent submission score to the oldest for that element.
- **Upward trend** (latest > oldest): sparkline line colour is **green** (`#137B4D` per design system).
- **Downward or flat trend** (latest ≤ oldest): sparkline line colour is **blue** (`#005BAB` per design system).

### Tooltip
Hovering over any data point on the sparkline shows a tooltip: `"Score: {score} — {date}"` (e.g. `"Score: 4 — 23 Jun 2026"`).

---

## Acceptance Criteria

**AC1 — A sparkline chart is rendered in each element group header row**  
Given a user has submissions for "HCP Engagement" and "Brand Planning",  
When the `/history` page loads,  
Then a sparkline chart element is visible in the row for "HCP Engagement" and a separate sparkline is visible in the row for "Brand Planning".

**AC2 — Sparkline shows one data point per submission in chronological order**  
Given a user has 3 submissions for "HCP Engagement" at T1 < T2 < T3 with scores 2, 3, 4,  
When the "HCP Engagement" sparkline renders,  
Then it contains exactly 3 data points ordered T1 → T2 → T3 from left to right (ascending chronological order).

**AC3 — Upward trend renders in green; flat or downward trend renders in blue**  
Given one element has scores [2, 3, 4] (upward: latest 4 > oldest 2) and another has scores [4, 3, 2] (downward: latest 2 < oldest 4),  
When the sparklines render,  
Then the first sparkline's line colour is green (`#137B4D`) and the second's is blue (`#005BAB`).

**AC4 — Hovering over a sparkline data point shows a tooltip with score and date**  
Given a sparkline has a data point at T2 with score 3,  
When the user hovers over that data point,  
Then a tooltip appears showing the score (3) and the submission date in a human-readable format (e.g. "10 Jun 2026").

**AC5 — An element with only one submission shows a single-point flat line without errors**  
Given a user has exactly 1 submission for "Brand Planning",  
When the "Brand Planning" sparkline renders,  
Then a single visible data point is shown (or a minimal flat line), no JavaScript error appears in the console, and the page does not crash.

---

## Edge Cases

- **Two submissions with equal scores**: latest equals oldest — classified as "flat", renders in blue.
- **Score goes up then down** (e.g. 2, 4, 3): trend direction is based only on oldest vs latest — 2 vs 3 is upward, renders green even though the last step declined.
- **Maximum data points** (e.g. 20 submissions for one element): sparkline must not overflow its container; x-axis points are compressed to fit.
- **Sparkline tooltip on mobile/touch**: tooltip must be accessible via tap, not just hover.

---

## Out of Scope
- A full time-series chart or line graph — the sparkline is a compact, inline-only visual.
- Filtering or sorting by trend direction.
- Sparklines per task (only per element).

## Dependencies
- PROT-109 (`/history` page) must exist; this ticket modifies its layout to group by element.
- PROT-108 (`GET /api/assessments`) provides the submission data; the sparkline uses the same payload.

## Definition of Done
- [ ] `/history` page layout updated to group submissions by element
- [ ] Sparkline renders in each element group header row
- [ ] All 5 acceptance criteria pass as named Playwright scenarios
- [ ] Single-data-point edge case has an explicit scenario
- [ ] The generated Gherkin feature file covers each AC as a distinct scenario
