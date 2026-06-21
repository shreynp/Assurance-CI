# PROT-108 — Add GET /api/assessments endpoint to list the authenticated user's submissions

**Type**: API story
**Test type**: pytest-bdd

## Description
There is currently no way to retrieve previously submitted assessments via the API. Add a GET endpoint that returns a paginated list of the authenticated user's submissions, sorted by submission date descending.

## Acceptance Criteria
- AC1: GET /api/assessments returns 200 with an array of assessment objects and a `total` count
- AC2: Each item includes `id`, `element`, `task`, `selfScore`, `rationale`, and `submittedAt`
- AC3: Results are sorted by `submittedAt` descending (most recent first)
- AC4: The endpoint supports `?limit` and `?offset` query params for pagination
- AC5: Only assessments belonging to the authenticated user are returned; other users' records are never exposed
