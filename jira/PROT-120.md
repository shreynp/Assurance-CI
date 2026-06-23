# PROT-120 — Add role guard redirecting non-admin users away from /admin

**Type**: Story  
**Priority**: High  
**Epic**: Admin Panel  
**Test type**: Playwright  

---

## User Story
As a platform operator, I want the `/admin` page to be accessible only to users with the `admin` role, so that contributors cannot view other users' assessment data and unauthenticated visitors cannot reach the admin dashboard at all.

## Business Context
The `/admin` page (PROT-119) displays assessment records from all contributors in a market. Without a role guard, any authenticated contributor could navigate to `/admin` and view their colleagues' scores — a privacy violation and a compliance risk. The guard must stop unauthorised access before any admin data is fetched or rendered, both on the client side (to prevent flash-of-admin-content) and on the server side (to prevent the admin API call from being made). A clear toast message after redirect tells the user why they were sent away, preventing confusion.

---

## Description

Add a role guard to the `/admin` page that enforces access control at two levels:

1. **Server-side (middleware or SSR check)**: before the page renders, read the user's role from the session. If the role is not `"admin"`, redirect immediately to `/assessment` (authenticated non-admin) or `/login` (unauthenticated).

2. **Client-side (React/Next.js guard component)**: on mount, call `GET /api/user/me` (PROT-105) and check the `role` field. If not `"admin"`, redirect before any admin API call fires. This catches cases where server-side rendering is not available.

When a non-admin contributor is redirected to `/assessment`, a toast notification must appear on the `/assessment` page with the message: **"You do not have permission to access the admin area."**

The toast must not appear on the login redirect — unauthenticated users are simply redirected to login silently.

---

## Acceptance Criteria

- AC1: Contributor navigating to /admin is redirected to /assessment
- AC2: Toast message appears on /assessment after the redirect
- AC3: Redirect happens before any admin data is fetched
- AC4: Admin user can access /admin without any redirect
- AC5: Unauthenticated user navigating to /admin is redirected to the login page


**AC1 — Contributor navigating to /admin is redirected to /assessment**  
Given a logged-in user with `role: "contributor"` navigates directly to `/admin`,  
When the page attempts to load,  
Then the browser URL changes to `/assessment` and the `/admin` page content (contributor table) is never rendered.

**AC2 — Toast message appears on /assessment after the redirect**  
Given a contributor was redirected from `/admin` to `/assessment`,  
When the `/assessment` page loads after the redirect,  
Then a toast notification is visible on screen containing the text "You do not have permission to access the admin area."

**AC3 — Redirect happens before any admin data is fetched**  
Given a contributor navigates to `/admin`,  
When the guard runs,  
Then no request to `GET /api/admin/assessments` is made (Playwright: assert no network call to that path before the redirect fires).

**AC4 — Admin user can access /admin without any redirect**  
Given a logged-in user with `role: "admin"` navigates to `/admin`,  
When the page loads,  
Then the browser URL remains `/admin` and the admin summary table is rendered.

**AC5 — Unauthenticated user navigating to /admin is redirected to the login page**  
Given a user with no active session navigates to `/admin`,  
When the guard runs,  
Then the browser URL changes to `/login` (or the root login route) and no admin content or toast message is shown.

---

## Edge Cases

- **Direct URL navigation** (typing `/admin` in the address bar, not via in-app link): guard must still fire — it cannot rely on navigation guards that only trigger on SPA route transitions.
- **`GET /api/user/me` is slow or fails**: show a loading state for max 3 seconds, then redirect to `/login` as a safe fallback (do not render the admin page while waiting indefinitely).
- **Role changes mid-session**: if a contributor is promoted to admin while their session is active, they must re-authenticate (new token) for the guard to recognise the new role — no hot-patching of role in active sessions.
- **Viewer role**: treated the same as contributor — redirected to `/assessment` with the toast.
- **Toast dismissal**: the toast should auto-dismiss after 5 seconds or be manually closable by the user.

---

## Out of Scope
- Locking down the API endpoint `GET /api/admin/assessments` — that is enforced server-side in PROT-118.
- A permission denied page (`/403`) — the redirect to `/assessment` + toast is sufficient.

## Dependencies
- PROT-105 (`GET /api/user/me`) provides the `role` field the guard checks client-side.
- PROT-119 (`/admin` page) is the protected route this guard covers.
- PROT-118 (`GET /api/admin/assessments`) must also enforce role server-side as a defence-in-depth measure.

## Definition of Done
- [ ] Role guard exists and fires on direct URL navigation to `/admin`
- [ ] Network call to `/api/admin/assessments` is not made when a contributor is redirected (verified via Playwright network interception)
- [ ] All 5 acceptance criteria pass as named Playwright scenarios
- [ ] Unauthenticated redirect (AC5) has an explicit scenario
- [ ] The generated Gherkin feature file covers each AC as a distinct scenario
