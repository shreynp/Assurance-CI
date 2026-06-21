# PROT-115 — Add GET /api/assessments/:id/triangulation endpoint

**Type**: API story
**Test type**: pytest-bdd

## Description
The triangulated view needs a single endpoint that combines the user's self-score with the AI-generated score and the ICO benchmark for a specific assessment record. Add a /triangulation sub-resource that returns all three values and the computed delta flags.

## Acceptance Criteria
- AC1: GET /api/assessments/:id/triangulation returns 200 with `selfScore`, `aiScore`, `icoScore`, and `deltaFlags` array
- AC2: Each item in `deltaFlags` includes `element`, `selfScore`, `aiScore`, `gap`, and `direction` ("above" or "below")
- AC3: Only elements where the absolute gap between selfScore and aiScore exceeds 1 appear in `deltaFlags`
- AC4: A request for an assessment that belongs to a different user returns 403
- AC5: A request for a non-existent assessment ID returns 404
