# PROT-116 — Show AI score vs self score comparison table below spider chart on /triangulated

**Type**: Story  
**Priority**: Medium  
**Epic**: Triangulation Enhancements  
**Test type**: Playwright  

---

## User Story
As a market contributor reviewing my triangulated assessment, I want to see a precise comparison table listing exact scores for every element, so that I can read the specific numbers that the spider chart only shows approximately, and sort by gap to immediately find the elements where my scoring diverges most.

## Business Context
The spider chart on `/triangulated` is effective for communicating overall triangulation shape but its axes are hard to read precisely — a contributor cannot tell from the chart that their "Campaign Execution" self-score is exactly 2 vs. an AI score of 4. A comparison table directly below the chart gives the exact values for all five elements in a scannable format. Amber row highlighting calls out the flagged elements (gap > 1) without requiring the user to mentally compare numbers, and column sorting lets the user quickly rank elements by their gap.

---

## Description

Add a comparison table directly below the spider chart on the `/triangulated` page. The table is populated from the `GET /api/assessments/:id/triangulation` endpoint (PROT-115). It shows all five elements regardless of whether they are delta-flagged — it is a complete overview, not just the flagged list.

### Table columns
| Column | Content |
|--------|---------|
| Element | Element name string |
| Self Score | The user's `selfScore` (integer 1–5) |
| AI Score | The AI-generated `aiScore` (integer 1–5, or "—" if null) |
| ICO Benchmark | The `icoScore` (integer 1–5, or "—" if null) |
| Gap | `selfScore − aiScore` as a signed integer: `+2`, `−1`, `0` |

### Gap display rules
- Positive gap (self > AI, overestimate): `+N` (e.g. `+2`)
- Negative gap (self < AI, underestimate): `−N` (e.g. `−2`) — use a true minus sign `−` not a hyphen `-`
- Zero gap: `0`

### Row highlight rule
Rows where `abs(selfScore − aiScore) > 1` are highlighted with an amber background (`rgba(212,130,10,0.08)` per design system) to indicate a flagged divergence.

### Sorting
Clicking any column header sorts the table by that column. Clicking the same header again reverses the sort direction. Default sort is by Element name, ascending.

---

## Acceptance Criteria

- AC1: Table appears below spider chart with the five required columns
- AC2: Gap column shows signed numeric difference (selfScore − aiScore)
- AC3: Rows with absolute gap > 1 are highlighted amber
- AC4: Clicking a column header sorts the table by that column
- AC5: Table is visible at 1280×800 viewport without scrolling past the chart


**AC1 — Table appears below spider chart with the five required columns**  
Given the `/triangulated` page is loaded for a valid assessment,  
When the page renders,  
Then a table is visible below the spider chart with column headers: "Element", "Self Score", "AI Score", "ICO Benchmark", "Gap".

**AC2 — Gap column shows signed numeric difference (selfScore − aiScore)**  
Given an element with `selfScore: 2` and `aiScore: 4`,  
When its row renders in the table,  
Then the Gap cell displays `−2` (self below AI).

Given an element with `selfScore: 5` and `aiScore: 3`,  
When its row renders,  
Then the Gap cell displays `+2` (self above AI).

**AC3 — Rows with absolute gap > 1 are highlighted amber**  
Given an element has `selfScore: 2` and `aiScore: 4` (gap = 2, exceeds 1),  
When its row renders,  
Then the row has an amber background applied.

Given an element has `selfScore: 3` and `aiScore: 4` (gap = 1, does not exceed threshold),  
When its row renders,  
Then the row does not have an amber background.

**AC4 — Clicking a column header sorts the table by that column**  
Given the table is rendered with default sort by Element name,  
When the user clicks the "Gap" column header,  
Then the rows reorder by Gap value (ascending); clicking "Gap" again reverses to descending.

**AC5 — Table is visible at 1280×800 viewport without scrolling past the chart**  
Given a browser window set to 1280×800,  
When the `/triangulated` page is loaded,  
Then the comparison table's column headers are visible without the user scrolling below the bottom edge of the spider chart.

---

## Edge Cases

- **`aiScore: null`** (AI not yet computed): display "—" in the AI Score and ICO Benchmark cells; the Gap cell displays "—" (cannot compute a gap).
- **All rows highlighted**: if all five elements have gap > 1, all five rows are amber — no special handling needed.
- **No rows highlighted**: if no element has gap > 1, no rows are amber; the table still renders normally.
- **Sort by Gap with null values**: null-gap rows sort to the bottom in both ascending and descending order.
- **ICO Benchmark null for some elements**: display "—" in that cell; the row renders normally.

---

## Out of Scope
- The Delta Flags section (which shows only flagged elements) — that is PROT-103.
- Confidence badges on the legend — that is PROT-117.
- Editing scores from this table.

## Dependencies
- PROT-115 (`GET /api/assessments/:id/triangulation`) provides the data for this table.
- PROT-103 (Delta Flags section) is a separate UI component that appears in the same page — they are independent.

## Definition of Done
- [ ] Comparison table renders below spider chart on `/triangulated`
- [ ] All 5 acceptance criteria pass as named Playwright scenarios
- [ ] Null `aiScore` scenario tested (shows "—" in AI Score and Gap columns)
- [ ] Sorting verified for each column header in Playwright
- [ ] The generated Gherkin feature file covers each AC as a distinct scenario
