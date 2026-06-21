# PROT-114 — Add GET /api/assessments/export endpoint returning CSV stream

**Type**: API story
**Test type**: pytest-bdd

## Description
The front-end export button needs a reliable API endpoint that returns assessment data as a downloadable CSV. Add an endpoint that streams the authenticated user's submissions as a properly formatted CSV with correct Content-Type and Content-Disposition headers.

## Acceptance Criteria
- AC1: GET /api/assessments/export returns 200 with Content-Type "text/csv"
- AC2: The response includes a Content-Disposition header with filename `assessments_export.csv`
- AC3: The CSV body starts with the header row: element,task,selfScore,rationale,submittedAt
- AC4: Each submission is a subsequent row with values correctly escaped (commas within rationale text are quoted)
- AC5: An authenticated user with no submissions receives a response with only the header row and a 200 status
