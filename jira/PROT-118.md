# PROT-118 — Add GET /api/admin/assessments returning all users' submissions (admin only)

**Type**: API story
**Test type**: pytest-bdd

## Description
Market administrators need visibility into all submissions across their market to monitor assessment progress. Add an admin endpoint that returns submissions from all users in the authenticated admin's market, with role enforcement.

## Acceptance Criteria
- AC1: GET /api/admin/assessments with an admin token returns 200 with all submissions for the admin's market
- AC2: Each record includes the submitting user's `name`, `email`, and their `selfScore`, `element`, and `submittedAt`
- AC3: A request from a non-admin user returns 403
- AC4: An admin user from Market A cannot see submissions from Market B
- AC5: The endpoint supports `?element` and `?user` query params to filter results
