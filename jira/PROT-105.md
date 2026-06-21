# PROT-105 — Add GET /api/user/me endpoint returning current user context

**Type**: API story
**Test type**: pytest-bdd

## Description
Front-end components need to know the authenticated user's name, market, and role without parsing JWT tokens client-side. Add a /api/user/me endpoint that returns the resolved user object from the active session.

## Acceptance Criteria
- AC1: GET /api/user/me with a valid session token returns 200 with `id`, `name`, `email`, `market`, and `role` fields
- AC2: GET /api/user/me with no token returns 401
- AC3: The `role` field is one of "admin", "contributor", or "viewer"
- AC4: The `market` field matches the market assigned to the user's account
- AC5: Response includes a `sessionExpiresAt` ISO timestamp so the client can warn before expiry
