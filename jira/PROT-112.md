# PROT-112 — Add completeness progress ring showing how many elements have been scored

**Type**: UI story
**Test type**: Playwright

## Description
Users do not know how far through the assessment framework they are. Add a circular progress ring on the /assessment page that shows X/Y elements scored, updating live as the user submits each element.

## Acceptance Criteria
- AC1: A circular progress ring appears on the /assessment page showing "X of Y elements scored"
- AC2: The ring fills proportionally to the fraction of elements with at least one submission
- AC3: When all elements are scored the ring is fully filled and changes colour to green
- AC4: The ring count updates immediately after a successful assessment submission without a page reload
- AC5: The ring is visible on a 1280×800 viewport in the top section of the page
