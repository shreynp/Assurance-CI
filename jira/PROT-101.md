# PROT-101 — Add POST /api/assessments endpoint to persist self-assessment submissions

**Type**: Story  
**Priority**: High  
**Epic**: Assessment CRUD  
**Test type**: pytest-bdd  

---

## User Story
As a market contributor, I want my self-assessment scores to be saved server-side when I submit them, so that my data is not lost on page refresh and an auditable record exists for compliance review.

## Business Context
All assessment scores are currently computed and held in browser state only. There is no server record of what a user scored, when they scored it, or who submitted it. This means: (1) refreshing the page wipes the session, (2) there is nothing for the traceability register to link to, and (3) market managers cannot aggregate or review submissions across their team. This endpoint is the foundation for every other assessment feature — the history page (PROT-109), summary stats (PROT-110), triangulated view (PROT-115), CSV export (PROT-114), and admin dashboard (PROT-118) all depend on records created here.

---

## Description

Add a `POST /api/assessments` route handler to the Protect AI Next.js application. The endpoint receives a self-assessment submission from the authenticated user, validates all fields, persists the record to the data store, and returns the created record.

### Request payload (JSON body)
```json
{
  "market": "US",
  "element": "HCP Engagement",
  "task": "Identify top 20% of HCPs by prescribing potential",
  "selfScore": 4,
  "rationale": "We have a segmentation model but it has not been validated this cycle."
}
```

All five fields are required. `selfScore` must be an integer between 1 and 5 inclusive. `element` must exactly match one of the five recognised element names (case-sensitive).

### Recognised element names (exact strings)
- `"HCP Engagement"`
- `"Brand Planning"`
- `"Campaign Execution"`
- `"Patient Identification"`
- `"Media & Promotion"`

### Success response (HTTP 200)
```json
{
  "id": "assess_01J2XKPQ3W",
  "market": "US",
  "element": "HCP Engagement",
  "task": "Identify top 20% of HCPs by prescribing potential",
  "selfScore": 4,
  "rationale": "We have a segmentation model but it has not been validated this cycle.",
  "submittedAt": "2026-06-23T14:32:00.000Z",
  "userId": "user_abc123"
}
```

The `id` is server-generated. `submittedAt` is the server timestamp at the moment of persistence (UTC, ISO-8601). `userId` is taken from the validated Bearer token — not from the request body.

### Error responses
| Condition | HTTP status | Body |
|-----------|-------------|------|
| Missing required field | 400 | `{ "error": "Missing required field: <fieldName>" }` |
| `selfScore` not an integer 1–5 | 400 | `{ "error": "selfScore must be an integer between 1 and 5" }` |
| `element` not in recognised list | 400 | `{ "error": "element must be one of: HCP Engagement, Brand Planning, Campaign Execution, Patient Identification, Media & Promotion" }` |
| No Authorization header | 401 | `{ "code": "AUTH_REQUIRED", "error": "Unauthorized" }` |
| Invalid or expired Bearer token | 401 | `{ "code": "AUTH_REQUIRED", "error": "Unauthorized" }` |

---

## Acceptance Criteria

**AC1 — Valid submission is persisted and the full record is returned**  
Given an authenticated user sends `POST /api/assessments` with `market: "US"`, `element: "HCP Engagement"`, `task: "Identify top HCPs"`, `selfScore: 4`, and `rationale: "Good model"`,  
When the request is processed,  
Then the server responds with HTTP 200 and a JSON body containing all submitted fields, a generated `id`, a `submittedAt` ISO-8601 UTC timestamp, and the authenticated user's `userId`.

**AC2 — selfScore below range is rejected**  
Given an authenticated user sends the same payload but with `selfScore: 0`,  
When the request is processed,  
Then the server responds with HTTP 400 and `{ "error": "selfScore must be an integer between 1 and 5" }`.

**AC3 — selfScore above range is rejected**  
Given an authenticated user sends the same payload but with `selfScore: 6`,  
When the request is processed,  
Then the server responds with HTTP 400 and `{ "error": "selfScore must be an integer between 1 and 5" }`.

**AC4 — Unrecognised element name is rejected**  
Given an authenticated user sends a payload with `element: "Market Access"` (not in the recognised list),  
When the request is processed,  
Then the server responds with HTTP 400 and an error message listing the five valid element names.

**AC5 — Missing required field is rejected**  
Given an authenticated user sends a payload where `task` is absent entirely,  
When the request is processed,  
Then the server responds with HTTP 400 identifying `task` as the missing field.

**AC6 — Unauthenticated request is rejected before business logic runs**  
Given a `POST /api/assessments` request with no `Authorization` header,  
When the request hits the route handler,  
Then the server responds with HTTP 401 and body `{ "code": "AUTH_REQUIRED", "error": "Unauthorized" }`, and no record is written to the data store.

---

## Edge Cases

- `selfScore` sent as a decimal (e.g. `3.5`) — reject with HTTP 400; must be a whole integer.
- `selfScore` sent as a numeric string (e.g. `"4"`) — must not be silently coerced; reject with 400 if the type is wrong, or coerce and validate depending on the framework — document the choice in code.
- Empty string `rationale` (`""`) — accept; rationale is optional free-text and may be blank.
- `market` field — accept any non-empty string; market-level validation is out of scope for this endpoint.
- Same user submitting the same element twice — both records are persisted as separate rows with distinct `id` and `submittedAt` values; no deduplication.
- `element` with wrong capitalisation (e.g. `"hcp engagement"`) — reject with 400; comparison is case-sensitive.

---

## Out of Scope
- AI score generation — happens asynchronously after submission and is not part of this endpoint.
- Updating an existing submission — see PROT-107 (PATCH endpoint).
- Listing past submissions — see PROT-108 (GET endpoint).
- Admin visibility of other users' submissions — see PROT-118.

## Dependencies
- PROT-104 (Bearer token auth middleware) provides the authentication layer this endpoint relies on. Both can be built in parallel; PROT-104 must be merged before this endpoint is reachable in a protected environment.

## Definition of Done
- [ ] Route handler exists at `POST /api/assessments`
- [ ] All 6 acceptance criteria pass in the pytest-bdd test suite
- [ ] Edge cases (decimal score, missing field, wrong element casing) covered by explicit scenarios
- [ ] The generated Gherkin feature file names each AC as a distinct scenario
- [ ] The traceability register records a green gate run for this story ID
