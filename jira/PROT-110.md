# PROT-110 — Add GET /api/assessments/summary endpoint with per-element aggregate stats

**Type**: API story
**Test type**: pytest-bdd

## Description
The triangulated view needs average scores across all submissions to draw a meaningful spider chart baseline. Add a summary endpoint that aggregates all of the authenticated user's submissions by element, returning average self score and submission count per element.

## Acceptance Criteria
- AC1: GET /api/assessments/summary returns 200 with an array of objects keyed by element name
- AC2: Each object includes `element`, `averageSelfScore` (rounded to 2 decimal places), and `submissionCount`
- AC3: Elements with zero submissions are excluded from the response
- AC4: If the user has no submissions at all, the endpoint returns 200 with an empty array
- AC5: `averageSelfScore` is computed only over the authenticated user's own submissions
