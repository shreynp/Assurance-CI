# PROT-104 — Add Bearer token auth middleware to /api/assessments routes

**Type**: API story
**Test type**: pytest-bdd

## Description
The /api/assessments endpoint is currently unauthenticated. Any request without a valid session token should be rejected before hitting business logic. Add middleware that validates a Bearer token against the session store and returns 401 on missing or invalid credentials.

## Acceptance Criteria
- AC1: A POST /api/assessments request with no Authorization header returns 401
- AC2: A request with a malformed or expired Bearer token returns 401 with the message "Unauthorized"
- AC3: A request with a valid Bearer token proceeds to the endpoint and returns 200 on valid payload
- AC4: The 401 response body includes a `code` field set to "AUTH_REQUIRED"
- AC5: Valid token validation adds the authenticated user's ID to the request context for downstream handlers
