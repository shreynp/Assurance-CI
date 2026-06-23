# PROT-108 — Add GET /api/assessments endpoint to list the authenticated user's submissions

**Type**: Story  
**Priority**: High  
**Epic**: Assessment CRUD  
**Test type**: pytest-bdd  

---

## User Story
As a market contributor, I want to retrieve all of my previously submitted assessments from the API, so that the history page and other UI components can display my submission record and I can track what I have scored over time.

## Business Context
There is currently no way to retrieve previously submitted assessments via the API. The history page (PROT-109), the trend sparkline (PROT-111), and the completeness ring (PROT-112) all need a list of past submissions to render. Without this endpoint, the front end has no data to work with after a page load. The endpoint must also enforce user scoping — a contributor must never receive another user's submissions, which is a compliance requirement: assessment data contains self-reported performance scores that are personal to each contributor.

---

## Description

Add a `GET /api/assessments` route handler that returns a paginated list of the authenticated user's assessment submissions, sorted by `submittedAt` descending (most recent first).

### Query parameters
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | integer | 20 | Maximum number of records to return. Max allowed: 100. |
| `offset` | integer | 0 | Number of records to skip (zero-based). Used for pagination. |

### Success response (HTTP 200)
```json
{
  "total": 47,
  "limit": 20,
  "offset": 0,
  "items": [
    {
      "id": "assess_01J2XKPQ3W",
      "element": "HCP Engagement",
      "task": "Identify top 20% of HCPs by prescribing potential",
      "selfScore": 4,
      "rationale": "Good segmentation model in place.",
      "submittedAt": "2026-06-23T14:32:00.000Z"
    }
  ]
}
```

`total` is the count of all records matching the query (before pagination). `items` contains the paginated subset. The authenticated user's `userId` is resolved from the token — it is not a query parameter.

---

## Acceptance Criteria

- AC1: Valid request returns 200 with items array and total count
- AC2: Each item contains the required fields
- AC3: Results are sorted by submittedAt descending
- AC4: Pagination via ?limit and ?offset works correctly
- AC5: Only the authenticated user's own records are returned


**AC1 — Valid request returns 200 with items array and total count**  
Given an authenticated user has 3 submissions in the data store,  
When they send `GET /api/assessments`,  
Then the server responds with HTTP 200, `"total": 3`, and `"items"` containing 3 assessment objects.

**AC2 — Each item contains the required fields**  
Given a submission exists for element "HCP Engagement",  
When it appears in the response `items` array,  
Then the object includes `id`, `element`, `task`, `selfScore`, `rationale`, and `submittedAt`.

**AC3 — Results are sorted by submittedAt descending**  
Given a user has submissions at timestamps T1 < T2 < T3,  
When they call `GET /api/assessments`,  
Then the `items` array is ordered T3, T2, T1 (most recent first).

**AC4 — Pagination via ?limit and ?offset works correctly**  
Given a user has 5 submissions,  
When they call `GET /api/assessments?limit=2&offset=2`,  
Then `"items"` contains submissions 3 and 4 (zero-indexed), `"total"` is still 5, `"limit"` is 2, and `"offset"` is 2.

**AC5 — Only the authenticated user's own records are returned**  
Given user A has 5 submissions and user B has 3 submissions,  
When user A calls `GET /api/assessments`,  
Then the response contains exactly 5 items — all belonging to user A — and none of user B's records appear.

---

## Edge Cases

- **No submissions**: `GET /api/assessments` for a user with zero records returns HTTP 200 with `{ "total": 0, "items": [] }`.
- **`limit` greater than 100**: clamp to 100 and return at most 100 records; do not reject with 400.
- **`limit` or `offset` is a non-integer string** (e.g. `?limit=foo`): return HTTP 400 — `{ "error": "limit must be a positive integer" }`.
- **`offset` beyond total**: return HTTP 200 with an empty `items` array; `total` still reflects the full count.
- **Unauthenticated request**: return HTTP 401 before any DB query runs.

---

## Out of Scope
- Filtering submissions by element, date range, or score — that filtering is for PROT-118 (admin endpoint).
- Returning submissions for other users — see PROT-118.
- The `market` field is not included in list items; it is available on the full record if needed.

## Dependencies
- PROT-101 (POST endpoint) must exist for records to exist to list.
- PROT-104 (auth middleware) scopes results to the authenticated user.
- PROT-109 (history page) is the primary UI consumer of this endpoint.

## Definition of Done
- [ ] Route handler exists at `GET /api/assessments`
- [ ] All 5 acceptance criteria pass as named pytest-bdd scenarios
- [ ] Empty list, clamped limit, and out-of-bounds offset edge cases have explicit test coverage
- [ ] User scoping verified: user A cannot see user B's records
- [ ] The generated Gherkin feature file covers each AC as a distinct scenario
