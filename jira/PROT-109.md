# PROT-109 — Show assessment history list on /history page

**Type**: UI story
**Test type**: Playwright

## Description
Users have no view of what they have previously submitted. Add a /history page that lists all past assessment submissions for the logged-in user, with element name, self score, and submission date, fetched from GET /api/assessments.

## Acceptance Criteria
- AC1: The /history page renders a table with columns: Element, Task, Self Score, Submitted
- AC2: Rows are ordered most-recent-first
- AC3: Each row shows the `selfScore` as a filled star rating (e.g. ★★★☆☆ for score 3)
- AC4: An empty state message "No assessments submitted yet" is shown when the list is empty
- AC5: The page is visible and usable on a 1280×800 viewport without horizontal scrolling
