# PROT-103 — Show delta flag count and flagged elements on the triangulated view

**Type**: Story  
**Priority**: Medium  
**Epic**: Triangulation Enhancements  
**Test type**: Playwright  

---

## User Story
As a market contributor reviewing my triangulated assessment, I want to see which specific elements have a meaningful gap between my self-score and the AI score, so that I can focus improvement effort on the areas where my self-perception most diverges from the AI's evaluation rather than eyeballing the spider chart.

## Business Context
The `/triangulated` page renders a spider chart with three overlapping series (Self, AI, ICO). The `deltaFlags` array is already computed and returned by the triangulation API (`GET /api/assessments/:id/triangulation` — PROT-115), but it is never surfaced in the UI. Users can see the general shape of their triangulation chart but cannot quickly identify which specific elements are flagged or by how much. A contributor who scored "Campaign Execution" at 2 while the AI scored it at 4 needs that called out explicitly, not buried in a chart they must read carefully. This section makes the triangulation immediately actionable.

---

## Description

Below the spider chart on `/triangulated`, add a **"Delta Flags"** section. The section heading includes the count of flagged elements in parentheses (e.g. "Delta Flags (3)"). Each flagged element — defined as any element where the absolute gap between `selfScore` and `aiScore` exceeds 1 — appears as a structured row. If there are no flagged elements, the section shows an empty-state message instead.

### Data source
The `deltaFlags` array from `GET /api/assessments/:id/triangulation`:
```json
{
  "deltaFlags": [
    {
      "element": "Campaign Execution",
      "selfScore": 2,
      "aiScore": 4,
      "gap": 2,
      "direction": "below"
    }
  ]
}
```
`direction: "below"` means self-score is below the AI score (user underestimates). `direction: "above"` means self-score is above the AI score (user overestimates).

### Row format
```
Campaign Execution    Self: 2 · AI: 4 · Gap: −2 ↓
HCP Engagement        Self: 5 · AI: 3 · Gap: +2 ↑
```
- `direction: "below"`: gap rendered with `−` prefix and a `↓` indicator
- `direction: "above"`: gap rendered with `+` prefix and a `↑` indicator

---

## Acceptance Criteria

- AC1: Section heading appears below the spider chart with the flagged count
- AC2: Each flagged element row shows the element name, both scores, and the signed gap
- AC3: Elements with gap ≤ 1 are excluded from the list
- AC4: Empty state is shown when no elements are flagged
- AC5: Section is visible at 1280×800 viewport without scrolling past the spider chart


**AC1 — Section heading appears below the spider chart with the flagged count**  
Given the `/triangulated` page is loaded for an assessment whose triangulation response includes 2 delta flags,  
When the page fully renders,  
Then a section heading reading "Delta Flags (2)" is visible directly below the spider chart.

**AC2 — Each flagged element row shows the element name, both scores, and the signed gap**  
Given the `deltaFlags` array contains an entry for "Campaign Execution" with `selfScore: 2`, `aiScore: 4`, `gap: 2`, `direction: "below"`,  
When the Delta Flags section renders,  
Then a row is visible that shows "Campaign Execution", "Self: 2", "AI: 4", and "Gap: −2 ↓" (exact format may vary but all four data points must be present and unambiguous).

**AC3 — Elements with gap ≤ 1 are excluded from the list**  
Given the triangulation response includes an entry for "HCP Engagement" with `selfScore: 3`, `aiScore: 4`, `gap: 1`,  
When the Delta Flags section renders,  
Then "HCP Engagement" does not appear anywhere in the flagged list.

**AC4 — Empty state is shown when no elements are flagged**  
Given the triangulation response returns `"deltaFlags": []`,  
When the Delta Flags section renders,  
Then the heading reads "Delta Flags (0)" and the body shows exactly "No significant gaps detected" — no rows, no table.

**AC5 — Section is visible at 1280×800 viewport without scrolling past the spider chart**  
Given a browser window set to 1280×800,  
When the `/triangulated` page is loaded with at least one delta flag,  
Then the Delta Flags section heading and at least the first row are visible within the initial viewport — the user does not need to scroll past the bottom of the chart to see them.

---

## Edge Cases

- **All five elements flagged**: the section must list all five rows without collapsing, truncating, or paginating.
- **`direction: "above"`** (user overestimates vs AI): render gap as `+N ↑` to make overconfidence visually distinct from underestimation.
- **Maximum possible gap** (selfScore 1, aiScore 5, gap 4): must display correctly with no value clamping.
- **`deltaFlags` key absent from API response**: treat as an empty array; show "No significant gaps detected".
- **Tie-breaking when all gaps are exactly 1**: none of those elements appear in the list (≤ 1 is excluded, per AC3); the section shows the empty state.

---

## Out of Scope
- Sorting or filtering the flagged element rows by gap size.
- ICO score gap flagging — this ticket flags only the Self vs AI gap.
- Coaching recommendations linked to flagged elements.
- The comparison table that shows all five elements (flagged and unflagged) — that is PROT-116.

## Dependencies
- PROT-115 (triangulation API endpoint) provides the `deltaFlags` data. This UI ticket can be built and tested with mock API data; PROT-115 must be merged for full end-to-end test runs.

## Definition of Done
- [ ] Delta Flags section renders below the spider chart on `/triangulated`
- [ ] Section heading dynamically shows the correct flagged count
- [ ] Empty state tested with a dedicated Playwright scenario
- [ ] All 5 acceptance criteria pass as named Playwright scenarios
- [ ] The generated Gherkin feature file covers each AC as a distinct scenario
