# PROT-105 — Add GET /api/user/me endpoint returning current user context

**Type**: Story  
**Priority**: High  
**Epic**: Auth & User Context  
**Test type**: pytest-bdd  

---

## User Story
As a front-end component, I want a single endpoint to retrieve the authenticated user's full profile from the active session, so that the UI can display the user's name and market without parsing JWT tokens client-side and can enforce role-based visibility decisions.

## Business Context
Multiple front-end components need to know who the logged-in user is: the nav header chip (PROT-106) shows name and market; the admin guard (PROT-120) checks the role; the assessment submission (PROT-101) must attribute to the correct user. Parsing JWT tokens in the browser is brittle (token format can change, clock skew causes inconsistencies) and exposes internal claims to client-side code. A single server-side `/api/user/me` endpoint resolves the session, returns a clean, versioned user object, and also surfaces the session expiry time so the UI can warn users before they are logged out mid-assessment.

---

## Description

Add a `GET /api/user/me` route handler that reads the Bearer token from the `Authorization` header, resolves the corresponding session, and returns the authenticated user's profile object.

### Success response (HTTP 200)
```json
{
  "id": "user_abc123",
  "name": "Shreyas Jagannath",
  "email": "shreyas.jagannath@newpage.io",
  "market": "US",
  "role": "contributor",
  "sessionExpiresAt": "2026-06-23T22:00:00.000Z"
}
```

`role` is one of three exact string values: `"admin"`, `"contributor"`, or `"viewer"`. `market` is the market code assigned to the user's account at registration (e.g. `"US"`, `"UK"`, `"DE"`). `sessionExpiresAt` is the UTC ISO-8601 expiry timestamp of the current session — derived from the session store or JWT `exp` claim, not recomputed.

### Error response (HTTP 401)
```json
{ "code": "AUTH_REQUIRED", "error": "Unauthorized" }
```

---

## Acceptance Criteria

**AC1 — Valid session token returns the full user profile**  
Given a `GET /api/user/me` request with a valid Bearer token for user `user_abc123`,  
When the request is processed,  
Then the server responds with HTTP 200 and a JSON body containing `id`, `name`, `email`, `market`, `role`, and `sessionExpiresAt`.

**AC2 — Request with no token returns 401**  
Given a `GET /api/user/me` request with no `Authorization` header,  
When the request is processed,  
Then the server responds with HTTP 401 and `{ "code": "AUTH_REQUIRED", "error": "Unauthorized" }`.

**AC3 — `role` field is one of the three valid values**  
Given a valid session for a user whose assigned role is `"contributor"`,  
When `GET /api/user/me` is called,  
Then the response body contains `"role": "contributor"` — not a number, not null, not any other string.

**AC4 — `market` field matches the user's assigned market**  
Given a valid session for a user assigned to the `"US"` market,  
When `GET /api/user/me` is called,  
Then the response body contains `"market": "US"`.

**AC5 — `sessionExpiresAt` is a future ISO-8601 UTC timestamp for an active session**  
Given a valid session that has not yet expired,  
When `GET /api/user/me` is called,  
Then `sessionExpiresAt` is a valid ISO-8601 string representing a UTC datetime in the future (relative to server time at the moment of the response).

---

## Edge Cases

- User account exists but their role has been changed in the data store since the token was issued — the endpoint must return the current role from the source of record, not the role encoded in the JWT at issue time.
- `market` field is `null` or absent in the user record (e.g. incomplete account setup) — return HTTP 500 with an internal error; do not return a partial user object that omits `market`.
- Session exists but is expired — return HTTP 401, same as missing token.
- Concurrent calls with the same valid token — each returns the same user object; no state mutation from a GET.

---

## Out of Scope
- Updating user profile fields — this endpoint is read-only.
- Token refresh — a separate concern; this endpoint only reads current session state.
- Listing all users — see PROT-118 (admin endpoint).

## Dependencies
- PROT-104 (auth middleware) handles token validation; this endpoint reuses the same validation layer. Both can be built simultaneously.
- PROT-106 (nav header chip) and PROT-120 (role guard) are direct consumers of this endpoint.

## Definition of Done
- [ ] Route handler exists at `GET /api/user/me`
- [ ] All 5 acceptance criteria pass as named pytest-bdd scenarios
- [ ] `sessionExpiresAt` expiry-boundary scenario tested explicitly
- [ ] The generated Gherkin feature file covers each AC as a distinct scenario
