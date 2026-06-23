# PROT-107 — Add PATCH /api/assessments/:id to update a submitted assessment

**Type**: Story  
**Priority**: Medium  
**Epic**: Assessment CRUD  
**Test type**: pytest-bdd  

---

## User Story
As a market contributor, I want to correct my self-score or rationale on a previously submitted assessment, so that honest mistakes do not pollute the historical record and I do not need to submit a duplicate entry to override an earlier one.

## Business Context
After submitting an assessment a contributor may realise their score was inflated (they misread the task description) or their rationale was incomplete. Without an edit endpoint the only recourse is to submit a second record for the same element, which creates a noisy history. A PATCH endpoint allows in-place correction with an `updatedAt` audit stamp — the original `submittedAt` is preserved so the history is not falsified, but the corrected values are what the system uses for summary and triangulation. Ownership validation ensures a contributor cannot overwrite a colleague's submission.

---

## Description

Add a `PATCH /api/assessments/:id` route handler. The endpoint accepts a partial update for `selfScore` and/or `rationale` on an existing assessment record. It validates that the authenticated user owns the record, validates any new field values, persists the changes, and returns the full updated record.

Immutable fields that must not be accepted in the PATCH body: `id`, `userId`, `element`, `task`, `market`, `submittedAt`. If any of these are present in the request body they must be silently ignored (not rejected with 400) — the server always resolves them from the stored record.

### Request payload (JSON body — all fields optional)
```json
{
  "selfScore": 3,
  "rationale": "Updated: the segmentation model was validated last week."
}
```

### Success response (HTTP 200)
```json
{
  "id": "assess_01J2XKPQ3W",
  "market": "US",
  "element": "HCP Engagement",
  "task": "Identify top 20% of HCPs by prescribing potential",
  "selfScore": 3,
  "rationale": "Updated: the segmentation model was validated last week.",
  "submittedAt": "2026-06-23T14:32:00.000Z",
  "updatedAt": "2026-06-23T16:05:00.000Z",
  "userId": "user_abc123"
}
```

`submittedAt` is the original creation timestamp and must not change. `updatedAt` is set to the server time at the moment the PATCH is applied.

---

## Acceptance Criteria

**AC1 — Valid PATCH updates both selfScore and rationale and returns the full updated record**  
Given an authenticated user owns assessment `assess_01J2XKPQ3W` with `selfScore: 4`,  
When they send `PATCH /api/assessments/assess_01J2XKPQ3W` with `{ "selfScore": 3, "rationale": "Revised." }`,  
Then the server responds with HTTP 200 containing the full record with `selfScore: 3`, the new rationale, and `updatedAt` set to the current server time.

**AC2 — Response includes updatedAt set to the current server time**  
Given a valid PATCH request for an owned assessment,  
When the server processes it,  
Then the response body includes an `updatedAt` field that is a valid ISO-8601 UTC timestamp representing the time of the update, and `submittedAt` is unchanged from the original creation time.

**AC3 — PATCH for an assessment owned by a different user returns 403**  
Given user A owns assessment `assess_A1` and user B is authenticated,  
When user B sends `PATCH /api/assessments/assess_A1` with a valid payload,  
Then the server responds with HTTP 403 and does not modify the record.

**AC4 — selfScore outside 1–5 returns 400**  
Given an authenticated user owns assessment `assess_01J2XKPQ3W`,  
When they send `PATCH /api/assessments/assess_01J2XKPQ3W` with `{ "selfScore": 0 }`,  
Then the server responds with HTTP 400 and `{ "error": "selfScore must be an integer between 1 and 5" }`.

**AC5 — Non-existent assessment ID returns 404**  
Given an authenticated user sends `PATCH /api/assessments/assess_DOESNOTEXIST` with a valid payload,  
When the server processes the request,  
Then the server responds with HTTP 404.

---

## Edge Cases

- **PATCH with only `selfScore` (no `rationale`)**: the stored `rationale` must not be cleared; only the supplied fields are updated.
- **PATCH with only `rationale` (no `selfScore`)**: the stored `selfScore` must not be reset; only `rationale` is updated.
- **PATCH with an empty body `{}`**: return HTTP 400 — a PATCH with no updatable fields is not meaningful.
- **PATCH supplying `element` (immutable field)**: silently ignore `element` in the body; update only the mutable fields that are present.
- **Multiple successive PATCHes**: each successive PATCH updates `updatedAt` to the new server time; `submittedAt` is never touched.
- **Concurrent PATCHes on the same record**: last-writer-wins is acceptable; no optimistic locking required in this prototype.

---

## Out of Scope
- Deleting an assessment record.
- Editing `element`, `task`, or `market` — these are immutable after creation.
- Admin ability to edit another user's submission.

## Dependencies
- PROT-101 (POST endpoint) must exist for records to exist to PATCH.
- PROT-104 (auth middleware) provides the authenticated user context used for ownership validation.

## Definition of Done
- [ ] Route handler exists at `PATCH /api/assessments/:id`
- [ ] All 5 acceptance criteria pass as named pytest-bdd scenarios
- [ ] Partial update (score only, rationale only) edge cases have explicit test coverage
- [ ] `submittedAt` immutability verified in tests
- [ ] The generated Gherkin feature file covers each AC as a distinct scenario
