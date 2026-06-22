# PROT-101 — Add POST /api/assessments endpoint to persist self-assessment submissions

**Type**: API story
**Test type**: pytest-bdd

## Description
Currently all assessment scores are computed client-side and lost on page refresh. Markets need an audit trail. Add a server-side API route that accepts a self-assessment submission and stores it.

## Acceptance Criteria
- AC1: The endpoint accepts a POST request with market, element, task, selfScore (1–5), and rationale
- AC2: It returns a 200 response with an assessment ID and the submission timestamp
- AC3: It returns a 400 error if selfScore is outside the 1–5 range
- AC4: It returns a 400 error if the element value is not a recognised element name. The recognised element names are: "HCP Engagement", "Brand Planning", "Campaign Execution", "Patient Identification", "Media & Promotion"
