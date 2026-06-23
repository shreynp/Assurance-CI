# PROT-118 — Add GET /api/admin/assessments returning all users' submissions (admin only)

**Type**: Story  
**Priority**: High  
**Epic**: Admin Panel  
**Test type**: pytest-bdd  

---

## User Story
As a market administrator, I want to retrieve all assessment submissions from every contributor in my market, so that I can monitor team-wide assessment progress, identify contributors who have not yet started, and review score distributions without asking each contributor to export their own data separately.

## Business Context
Market administrators are responsible for overseeing assessment completion across their team. The per-user `GET /api/assessments` endpoint (PROT-108) only returns the authenticated user's own data — by design, it cannot be used to aggregate across contributors. A separate admin endpoint is required that: (1) enforces the `admin` role (non-admins receive 403), (2) scopes results to the admin's own market (an admin in the US cannot access UK data), and (3) includes the submitting user's identity fields alongside the submission data, enabling the admin dashboard (PROT-119) to populate its contributor table.

---

## Description

Add a `GET /api/admin/assessments` route handler. The endpoint returns all assessment submissions from all users whose `market` matches the authenticated admin's market. Role enforcement is applied before any data query runs.

### Query parameters
| Parameter | Type | Description |
|-----------|------|-------------|
| `element` | string | Filter by exact element name (e.g. `?element=HCP+Engagement`) |
| `user` | string | Filter by user ID (e.g. `?user=user_abc123`) |

Both filters are optional and combinable. When neither is supplied, all submissions for the admin's market are returned (no pagination limit in this prototype — admin sees the full dataset).

### Success response (HTTP 200)
```json
{
  "market": "US",
  "total": 47,
  "items": [
    {
      "id": "assess_01J2XKPQ3W",
      "element": "HCP Engagement",
      "task": "Identify top 20% of HCPs by prescribing potential",
      "selfScore": 4,
      "submittedAt": "2026-06-23T14:32:00.000Z",
      "user": {
        "id": "user_abc123",
        "name": "Shreyas Jagannath",
        "email": "shreyas.jagannath@newpage.io"
      }
    }
  ]
}
```

`rationale` is intentionally excluded from the admin list view to prevent unnecessary exposure of free-text personal rationale at scale. The full record (including rationale) is available via `GET /api/assessments/:id` by the owning user.

---

## Acceptance Criteria

**AC1 — Admin request returns 200 with all submissions for the admin's market**  
Given an admin user authenticated for the "US" market, and 5 submissions exist from contributors in the "US" market,  
When they call `GET /api/admin/assessments`,  
Then the server responds with HTTP 200 and `"items"` containing all 5 submissions, with `"market": "US"` in the response body.

**AC2 — Each item includes user name, email, selfScore, element, and submittedAt**  
Given a submission by user "Shreyas Jagannath" for "HCP Engagement" with `selfScore: 4`,  
When it appears in the admin response,  
Then the item contains `element: "HCP Engagement"`, `selfScore: 4`, `submittedAt`, and a `user` object with `name: "Shreyas Jagannath"` and `email`.

**AC3 — Non-admin user receives 403**  
Given a contributor (role: "contributor") calls `GET /api/admin/assessments` with a valid token,  
When the request is processed,  
Then the server responds with HTTP 403 and no submission data is returned.

**AC4 — Admin user cannot see submissions from a different market**  
Given an admin for the "US" market calls `GET /api/admin/assessments` and 3 submissions exist from the "UK" market,  
When the request is processed,  
Then none of the UK market submissions appear in the response.

**AC5 — ?element and ?user query params filter the results correctly**  
Given 10 submissions exist across multiple elements and users for the "US" market,  
When the admin calls `GET /api/admin/assessments?element=HCP+Engagement&user=user_abc123`,  
Then the response contains only submissions that match both `element: "HCP Engagement"` AND `userId: "user_abc123"`.

---

## Edge Cases

- **Admin with no contributors in their market**: return HTTP 200 with `{ "market": "US", "total": 0, "items": [] }`.
- **`?element` filter with a value not in the recognised list**: return HTTP 400; do not silently return an empty array.
- **`?user` filter for a user from a different market**: return an empty array (the user exists but not in the admin's market scope); do not return 403 or expose that the user ID is valid.
- **Unauthenticated request**: return HTTP 401 before any role check or data query.
- **Viewer role (not admin, not contributor)**: return 403 same as contributor.

---

## Out of Scope
- Admin viewing submissions across multiple markets.
- Admin editing or deleting a contributor's submission.
- The `rationale` field in the list response — excluded by design.

## Dependencies
- PROT-104 (auth middleware) validates the Bearer token.
- PROT-105 (`GET /api/user/me`) or equivalent session resolution provides the admin's `market` and `role` for scoping.
- PROT-119 (`/admin` page) is the primary UI consumer.

## Definition of Done
- [ ] Route handler exists at `GET /api/admin/assessments`
- [ ] All 5 acceptance criteria pass as named pytest-bdd scenarios
- [ ] Cross-market isolation verified with a two-market test fixture
- [ ] `?element` + `?user` combined filter has an explicit test scenario
- [ ] The generated Gherkin feature file covers each AC as a distinct scenario
