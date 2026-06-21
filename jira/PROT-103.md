# PROT-103 — Show delta flag count and flagged elements on the triangulated view

**Type**: UI story
**Test type**: Playwright

## Description
The /triangulated page already renders a spider chart comparing Self vs AI vs ICO scores. The deltaFlags data exists but is not surfaced in the UI. Add a section below the chart listing each flagged element, the score gap, and which direction it diverged.

## Acceptance Criteria
- AC1: The /triangulated page shows a "Delta Flags" section below the spider chart
- AC2: Each flagged element appears as a row showing: element name, self score, AI score, and the gap (e.g. "Self: 2 · AI: 4 · Gap: +2")
- AC3: Elements with no delta flag (gap ≤ 1) do not appear in the list
- AC4: If there are no delta flags, the section shows "No significant gaps detected"
- AC5: The section is visible on a 1280×800 viewport without scrolling past the chart
