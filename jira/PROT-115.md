# PROT-115 — Add GET /api/assessments/:id/triangulation endpoint

**Type**: Story  
**Priority**: High  
**Epic**: Triangulation Enhancements  
**Test type**: pytest-bdd  

---

## User Story
As the triangulated view on `/triangulated`, I need a single endpoint that returns an assessment's self-score alongside the AI-generated score and the ICO benchmark, plus a pre-computed array of delta flags, so that the spider chart and comparison table can be rendered from one API call with no client-side score merging.

## Business Context
The `/triangulated` page is the centrepiece of the Assurance platform — it shows three perspectives on the same assessment: what the contributor scored themselves (self), what the AI estimated from their submissions (AI), and what the ICO sets as the target benchmark (ICO). Currently these three values exist in separate data silos and must be assembled client-side, which is fragile. Centralising the triangulation into a single endpoint means: (1) the client always gets a consistent, server-validated set of values; (2) delta flag computation is authoritative (not reimplemented in each front-end consumer); and (3) the triangulation logic can be unit-tested in isolation.

---

## Description

Add a `GET /api/assessments/:id/triangulation` route handler. Given an assessment ID, the endpoint assembles the self-score from the stored assessment, the AI score from the AI-generation service or cache, and the ICO benchmark from the benchmark data store, computes delta flags, and returns all four in a single response.

### Success response (HTTP 200)
```json
{
  "assessmentId": "assess_01J2XKPQ3W",
  "selfScore": 3,
  "aiScore": 4,
  "icoScore": 4,
  "confidences": {
    "self": null,
    "ai": 0.87,
    "ico": 0.95
  },
  "deltaFlags": [
    {
      "element": "Campaign Execution",
      "selfScore": 2,
      "aiScore": 4,
      "gap": 2,
      "direction": "below"
    }
  ]
}
```

`direction` is `"below"` when `selfScore < aiScore` (user underestimates) and `"above"` when `selfScore > aiScore` (user overestimates). `gap` is always the absolute value of `selfScore − aiScore`. Only elements where `gap > 1` appear in `deltaFlags`.

`confidences.self` is `null` (a contributor's self-score has no algorithmic confidence measure). `confidences.ai` and `confidences.ico` are floats between 0.0 and 1.0 representing the reliability estimate of each score source.

---

## Acceptance Criteria

- AC1: Returns 200 with selfScore, aiScore, icoScore, and deltaFlags
- AC2: Each deltaFlag item includes element, selfScore, aiScore, gap, and direction
- AC3: Only elements with gap > 1 appear in deltaFlags
- AC4: Assessment belonging to a different user returns 403
- AC5: Non-existent assessment ID returns 404


**AC1 — Returns 200 with selfScore, aiScore, icoScore, and deltaFlags**  
Given an authenticated user owns assessment `assess_01J2XKPQ3W` with `selfScore: 3` and the AI score for that element is 4, and the ICO benchmark is 4,  
When they call `GET /api/assessments/assess_01J2XKPQ3W/triangulation`,  
Then the server responds with HTTP 200 and a body containing `selfScore: 3`, `aiScore: 4`, `icoScore: 4`, and a `deltaFlags` array.

**AC2 — Each deltaFlag item includes element, selfScore, aiScore, gap, and direction**  
Given the assessment has `selfScore: 2` for element "Campaign Execution" and the AI score for that element is 4,  
When the endpoint computes delta flags,  
Then the `deltaFlags` array contains one object with `element: "Campaign Execution"`, `selfScore: 2`, `aiScore: 4`, `gap: 2`, `direction: "below"`.

**AC3 — Only elements with gap > 1 appear in deltaFlags**  
Given element "HCP Engagement" has `selfScore: 3` and `aiScore: 4` (gap = 1),  
When the endpoint computes delta flags,  
Then "HCP Engagement" does not appear in `deltaFlags` — a gap of exactly 1 is not flagged.

**AC4 — Assessment belonging to a different user returns 403**  
Given user A owns assessment `assess_A1` and user B is authenticated,  
When user B calls `GET /api/assessments/assess_A1/triangulation`,  
Then the server responds with HTTP 403.

**AC5 — Non-existent assessment ID returns 404**  
Given an authenticated user calls `GET /api/assessments/assess_DOESNOTEXIST/triangulation`,  
When the request is processed,  
Then the server responds with HTTP 404.

---

## Edge Cases

- **`aiScore` unavailable** (AI generation for this assessment has not completed): return the record with `aiScore: null` and an empty `deltaFlags` array; do not fail with 500.
- **`direction: "above"`** (selfScore > aiScore, user overestimates): gap is still the absolute difference; direction is `"above"`.
- **All five elements flagged**: all five appear in `deltaFlags`; no truncation.
- **`icoScore` unavailable for an element**: return `icoScore: null` for that element; the rest of the response is unaffected.
- **Unauthenticated request**: return HTTP 401 before any data is read.

---

## Out of Scope
- Triggering AI score generation — this endpoint reads a pre-computed AI score; it does not run the AI.
- Aggregating across multiple assessments — this is per-assessment only.
- Updating or storing delta flags separately — they are computed on the fly per request.

## Dependencies
- PROT-101 (POST endpoint) creates the assessment records this endpoint reads.
- PROT-104 (auth middleware) provides authentication and ownership context.
- PROT-103 (delta flags UI) and PROT-116 (comparison table UI) are direct consumers.
- PROT-117 (confidence badges) uses the `confidences` field in this response.

## Definition of Done
- [ ] Route handler exists at `GET /api/assessments/:id/triangulation`
- [ ] All 5 acceptance criteria pass as named pytest-bdd scenarios
- [ ] `aiScore: null` scenario (AI not yet computed) has explicit test coverage
- [ ] 403 ownership enforcement verified with a two-user test fixture
- [ ] The generated Gherkin feature file covers each AC as a distinct scenario
