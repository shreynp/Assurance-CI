# PROT-104 — Add Bearer token auth middleware to /api/assessments routes

**Type**: Story  
**Priority**: High  
**Epic**: Auth & User Context  
**Test type**: pytest-bdd  

---

## User Story
As a platform operator, I want all `/api/assessments` routes to reject requests without a valid Bearer token before any business logic runs, so that unauthenticated callers can never read or write assessment data and the audit trail is always attributed to a known user.

## Business Context
The `/api/assessments` endpoint (PROT-101) is currently open — any HTTP client can call it without identifying itself. This creates two risks: (1) anonymous submissions with no user attribution, breaking the audit trail; (2) unauthenticated reads of assessment data that should be user-scoped. Adding middleware that validates the Bearer token before the route handler runs centralises auth enforcement and ensures every downstream handler can trust that `req.context.userId` is set and verified.

---

## Description

Add a middleware function that intercepts all requests to `/api/assessments` (and sub-routes) before they reach the route handler. The middleware must:

1. Read the `Authorization` header and extract the Bearer token.
2. Validate the token against the session store (verify signature, check expiry, confirm the session exists and is active).
3. On success: attach the resolved user object (`{ id, name, email, market, role }`) to the request context under `req.context.user` and call `next()`.
4. On failure: respond immediately with HTTP 401 — do not call `next()`, do not execute any route handler logic.

The middleware applies to all HTTP methods on all routes under `/api/assessments/*`.

### Token format
Bearer token in the `Authorization` header:
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### 401 response body (all failure cases)
```json
{
  "code": "AUTH_REQUIRED",
  "error": "Unauthorized"
}
```

---

## Acceptance Criteria

- AC1: Request with no Authorization header returns 401
- AC2: Request with a malformed Bearer token returns 401
- AC3: Request with an expired Bearer token returns 401
- AC4: Request with a valid Bearer token reaches the route handler
- AC5: Validated user ID is available in the request context for downstream handlers


**AC1 — Request with no Authorization header returns 401**  
Given a `POST /api/assessments` request with no `Authorization` header at all,  
When the middleware processes the request,  
Then the server responds with HTTP 401, `{ "code": "AUTH_REQUIRED", "error": "Unauthorized" }`, and the route handler is never invoked.

**AC2 — Request with a malformed Bearer token returns 401**  
Given a `POST /api/assessments` request with `Authorization: Bearer not-a-valid-jwt`,  
When the middleware attempts to validate the token,  
Then the server responds with HTTP 401 and `{ "code": "AUTH_REQUIRED", "error": "Unauthorized" }`.

**AC3 — Request with an expired Bearer token returns 401**  
Given a `POST /api/assessments` request with a structurally valid JWT whose `exp` claim is in the past,  
When the middleware validates the token,  
Then the server responds with HTTP 401 and `{ "code": "AUTH_REQUIRED", "error": "Unauthorized" }`.

**AC4 — Request with a valid Bearer token reaches the route handler**  
Given a `POST /api/assessments` request with a valid, non-expired Bearer token issued for user `user_abc123`,  
When the middleware validates the token,  
Then `req.context.user.id` equals `"user_abc123"` and the route handler is invoked and returns 200 on a valid payload.

**AC5 — Validated user ID is available in the request context for downstream handlers**  
Given a valid Bearer token is provided for a user with `id: "user_abc123"`, `market: "US"`, and `role: "contributor"`,  
When the middleware successfully validates the token,  
Then `req.context.user` contains `{ id: "user_abc123", market: "US", role: "contributor" }` and is accessible to the route handler without re-querying the session store.

---

## Edge Cases

- `Authorization` header present but with wrong scheme (e.g. `Authorization: Basic dXNlcjpwYXNz`) — treat as missing; return 401.
- Token with a valid signature but for a user whose session has been explicitly revoked (e.g. after sign-out) — return 401; the middleware must check the active session store, not just the JWT signature.
- Token header present but the value is empty (e.g. `Authorization: Bearer `) — return 401.
- Concurrent requests with the same valid token — each resolves independently; no shared mutable state per-request.
- The middleware must apply to `GET`, `POST`, `PATCH`, and `DELETE` on `/api/assessments` and all sub-routes (e.g. `/api/assessments/summary`, `/api/assessments/export`).

---

## Out of Scope
- Role-based access control within assessments (admin vs contributor) — role is attached to context here but enforcement is per-endpoint.
- Token issuance or refresh — this middleware only validates; it does not mint new tokens.
- Rate limiting or brute-force protection.

## Dependencies
- No upstream dependency; this middleware is a prerequisite for PROT-101 (POST), PROT-107 (PATCH), and PROT-108 (GET) to operate correctly in a protected environment.

## Definition of Done
- [ ] Middleware function exists and is registered on all `/api/assessments/*` routes
- [ ] All 5 acceptance criteria pass as named pytest-bdd scenarios
- [ ] Expired-token and revoked-token scenarios have explicit test coverage
- [ ] The generated Gherkin feature file covers each AC as a distinct scenario
