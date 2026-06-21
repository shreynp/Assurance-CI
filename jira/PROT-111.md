# PROT-111 — Show self-score trend sparkline per element on /history

**Type**: UI story
**Test type**: Playwright

## Description
The /history page shows individual submissions but no trend over time. Add a sparkline chart next to each unique element row showing how self-score has changed across submissions, so users can see whether their confidence in an element is improving.

## Acceptance Criteria
- AC1: Each unique element in the history list has a sparkline chart rendered in its row
- AC2: The sparkline shows one data point per submission, ordered chronologically left to right
- AC3: An upward trend is indicated in green; a downward or flat trend in blue
- AC4: Hovering over a sparkline point shows a tooltip with the score and submission date
- AC5: Elements with only one submission show a flat single-point line, not an error
