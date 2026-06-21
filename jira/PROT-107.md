# PROT-107 — Add PATCH /api/assessments/:id to update a submitted assessment

**Type**: API story
**Test type**: pytest-bdd

## Description
Contributors sometimes realise they scored an element incorrectly after submission. Add a PATCH endpoint that allows updating `selfScore` and `rationale` on an existing assessment record, with ownership validation so users cannot edit another user's submissions.

## Acceptance Criteria
- AC1: PATCH /api/assessments/:id with valid `selfScore` and `rationale` returns 200 with the updated record
- AC2: The response includes an `updatedAt` timestamp set to the current server time
- AC3: A request to update an assessment belonging to a different user returns 403
- AC4: A request with `selfScore` outside 1–5 returns 400
- AC5: A request for a non-existent assessment ID returns 404
