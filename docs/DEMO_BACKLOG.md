# Demo Backlog — Assurance CI

Full catalog of simulated Jira stories used to demonstrate the Assurance CI pipeline. Each file in `/jira/` is the input the pipeline reads when a developer commits a matching story ID.

Stories are grouped by feature area to make it easy to select a coherent subset for a given demo run.

---

## Seed Stories (original three — used in CI pipeline validation)

| ID | Title | Type | Test type |
|----|-------|------|-----------|
| [PROT-101](../jira/PROT-101.md) | Add POST /api/assessments endpoint | API | pytest-bdd |
| [PROT-102](../jira/PROT-102.md) | Replace self-assessment numeric input with a range slider | UI | Playwright |
| [PROT-103](../jira/PROT-103.md) | Show delta flag count and flagged elements on the triangulated view | UI | Playwright |

---

## Auth & User Context

| ID | Title | Type | Test type |
|----|-------|------|-----------|
| [PROT-104](../jira/PROT-104.md) | Add Bearer token auth middleware to /api/assessments routes | API | pytest-bdd |
| [PROT-105](../jira/PROT-105.md) | Add GET /api/user/me endpoint returning current user context | API | pytest-bdd |
| [PROT-106](../jira/PROT-106.md) | Show logged-in user name and market in the nav header | UI | Playwright |

---

## Assessment CRUD

| ID | Title | Type | Test type |
|----|-------|------|-----------|
| [PROT-107](../jira/PROT-107.md) | Add PATCH /api/assessments/:id to update a submitted assessment | API | pytest-bdd |
| [PROT-108](../jira/PROT-108.md) | Add GET /api/assessments endpoint listing the user's submissions | API | pytest-bdd |
| [PROT-109](../jira/PROT-109.md) | Show assessment history list on /history page | UI | Playwright |

---

## Analytics

| ID | Title | Type | Test type |
|----|-------|------|-----------|
| [PROT-110](../jira/PROT-110.md) | Add GET /api/assessments/summary with per-element aggregate stats | API | pytest-bdd |
| [PROT-111](../jira/PROT-111.md) | Show self-score trend sparkline per element on /history | UI | Playwright |
| [PROT-112](../jira/PROT-112.md) | Add completeness progress ring showing how many elements have been scored | UI | Playwright |

---

## CSV Export

| ID | Title | Type | Test type |
|----|-------|------|-----------|
| [PROT-113](../jira/PROT-113.md) | Add "Export as CSV" button on /history page | UI | Playwright |
| [PROT-114](../jira/PROT-114.md) | Add GET /api/assessments/export endpoint returning CSV stream | API | pytest-bdd |

---

## Triangulation Enhancements

| ID | Title | Type | Test type |
|----|-------|------|-----------|
| [PROT-115](../jira/PROT-115.md) | Add GET /api/assessments/:id/triangulation endpoint | API | pytest-bdd |
| [PROT-116](../jira/PROT-116.md) | Show AI score vs self score comparison table below spider chart | UI | Playwright |
| [PROT-117](../jira/PROT-117.md) | Add confidence score badge next to each data source label | UI | Playwright |

---

## Admin Panel

| ID | Title | Type | Test type |
|----|-------|------|-----------|
| [PROT-118](../jira/PROT-118.md) | Add GET /api/admin/assessments returning all users' submissions | API | pytest-bdd |
| [PROT-119](../jira/PROT-119.md) | Add /admin page with summary table of assessments across all contributors | UI | Playwright |
| [PROT-120](../jira/PROT-120.md) | Add role guard redirecting non-admin users away from /admin | UI | Playwright |

---

## Notifications

| ID | Title | Type | Test type |
|----|-------|------|-----------|
| [PROT-121](../jira/PROT-121.md) | Add POST /api/notifications to create an in-app alert | API | pytest-bdd |
| [PROT-122](../jira/PROT-122.md) | Show notification bell icon with unread count badge in the nav | UI | Playwright |
| [PROT-123](../jira/PROT-123.md) | Add POST /api/notifications/:id/read to mark a notification as read | API | pytest-bdd |

---

## Counts

| Dimension | Count |
|-----------|-------|
| Total stories | 23 |
| API stories (pytest-bdd) | 12 |
| UI stories (Playwright) | 11 |
| Feature areas | 7 |
