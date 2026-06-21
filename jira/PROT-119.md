# PROT-119 — Add /admin page with summary table of assessments across all market contributors

**Type**: UI story
**Test type**: Playwright

## Description
Admin users need a dashboard view to track assessment completion across their market team. Add an /admin page that shows a summary table of all contributors, how many elements they have scored, and their average self score.

## Acceptance Criteria
- AC1: The /admin page shows a summary table with columns: Contributor, Elements Scored, Average Self Score, Last Submission
- AC2: Rows are sorted by Elements Scored descending so the least-progressed contributors appear at the bottom
- AC3: Average Self Score is displayed to one decimal place
- AC4: Clicking a contributor row expands a detail panel showing that user's individual element scores
- AC5: The page is visible and usable on a 1280×800 viewport without horizontal scrolling
