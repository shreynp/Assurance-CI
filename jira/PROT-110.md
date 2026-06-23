# PROT-110 — Add GET /api/assessments/summary endpoint with per-element aggregate stats

**Type**: Story  
**Priority**: Medium  
**Epic**: Analytics  
**Test type**: pytest-bdd  

---

## User Story
As a front-end component rendering the triangulated spider chart, I want a summary endpoint that returns the user's average self-score per element aggregated across all submissions, so that the chart has a stable baseline to plot rather than relying on a single assessment record.

## Business Context
The triangulated spider chart on `/triangulated` needs a per-element average self-score to plot the "Self" series across the five elements (HCP Engagement, Brand Planning, Campaign Execution, Patient Identification, Media & Promotion). Using only the most recent submission per element would underrepresent scoring history; averaging across all submissions gives a more representative picture and reduces the impact of one-off outlier scores. The completeness ring (PROT-112) also uses this endpoint's `submissionCount` per element to determine which elements have been scored at all.

---

## Description

Add a `GET /api/assessments/summary` route handler. The endpoint aggregates all of the authenticated user's submissions by element, computing the average self-score and total submission count for each element that has at least one submission.

### Success response (HTTP 200)
```json
[
  {
    "element": "HCP Engagement",
    "averageSelfScore": 3.67,
    "submissionCount": 3
  },
  {
    "element": "Brand Planning",
    "averageSelfScore": 4.00,
    "submissionCount": 1
  }
]
```

`averageSelfScore` is the arithmetic mean of all `selfScore` values for that element, rounded to exactly 2 decimal places using standard rounding (0.5 rounds up). `submissionCount` is the total number of submissions for that element (not deduplicated — if the same element was submitted 3 times, `submissionCount` is 3). Elements with zero submissions are excluded from the array.

**Route ordering caveat**: this route must be registered before `GET /api/assessments/:id` to prevent the router from matching `"summary"` as an `:id` parameter.

---

## Acceptance Criteria

**AC1 — Returns 200 with an array of per-element aggregate objects**  
Given a user has submitted 3 assessments for "HCP Engagement" (scores 3, 4, 4) and 1 assessment for "Brand Planning" (score 4),  
When they call `GET /api/assessments/summary`,  
Then the server responds with HTTP 200 and an array containing exactly 2 objects — one for each element with at least one submission.

**AC2 — Each object includes element, averageSelfScore, and submissionCount**  
Given a user has 3 submissions for "HCP Engagement" with scores 3, 4, 4,  
When the summary is returned,  
Then the "HCP Engagement" object contains `"element": "HCP Engagement"`, `"averageSelfScore": 3.67`, and `"submissionCount": 3`.

**AC3 — Elements with zero submissions are excluded**  
Given a user has submissions for only 2 of the 5 elements,  
When they call `GET /api/assessments/summary`,  
Then the array contains exactly 2 objects — the 3 elements with no submissions do not appear in the response at all.

**AC4 — User with no submissions at all receives 200 with an empty array**  
Given an authenticated user has zero submissions,  
When they call `GET /api/assessments/summary`,  
Then the server responds with HTTP 200 and the response body is `[]`.

**AC5 — averageSelfScore is computed only over the authenticated user's own submissions**  
Given user A has 2 submissions for "Campaign Execution" with scores 2 and 4 (average 3.00), and user B has 1 submission for the same element with score 5,  
When user A calls `GET /api/assessments/summary`,  
Then the "Campaign Execution" object shows `"averageSelfScore": 3.00` — user B's score 5 is not included.

---

## Edge Cases

- **Single submission for an element** (submissionCount 1): `averageSelfScore` equals the single score as a float with 2 decimal places (e.g. `4.00`), not just `4`.
- **All submissions for one element** (e.g. all 10 are "HCP Engagement"): only one element appears in the array; the other 4 are excluded.
- **Rounding at exactly 0.5**: test with scores summing to an average of e.g. 3.5 or 2.5 — must round to 3.50 and 2.50 (two decimal places, half-up rounding).
- **Route collision with `:id`**: verify that `GET /api/assessments/summary` is not matched by the `GET /api/assessments/:id` route handler — route registration order is critical.
- **Unauthenticated request**: return HTTP 401 before any aggregation query runs.

---

## Out of Scope
- Per-task breakdown within an element — this aggregates at the element level only.
- Aggregation across all users — that is for PROT-118 (admin endpoint).
- Filtering by date range.

## Dependencies
- PROT-101 (POST endpoint) must exist to create the submissions being summarised.
- PROT-104 (auth middleware) scopes aggregation to the authenticated user.
- PROT-112 (completeness ring) and the spider chart on `/triangulated` are primary consumers of this endpoint.

## Definition of Done
- [ ] Route handler exists at `GET /api/assessments/summary` registered before `GET /api/assessments/:id`
- [ ] All 5 acceptance criteria pass as named pytest-bdd scenarios
- [ ] Rounding edge case (0.5) has an explicit test scenario
- [ ] User-scoping verified: user A's summary excludes user B's scores
- [ ] The generated Gherkin feature file covers each AC as a distinct scenario
