# PROT-106 — Show logged-in user name and market in the nav header

**Type**: Story  
**Priority**: Medium  
**Epic**: Auth & User Context  
**Test type**: Playwright  

---

## User Story
As a logged-in market contributor, I want to see my name and market displayed in the navigation bar, so that I can confirm I am operating under the correct identity and market context before submitting any assessment data.

## Business Context
After login there is no visible signal in the UI of who the user is or which market they are operating in. A contributor who manages multiple markets or logs in with different accounts has no way to confirm they are in the right context before scoring. Showing "Shreyas (US)" in the nav bar costs almost nothing and eliminates a category of data-quality errors (wrong-user submissions, wrong-market submissions). The chip also acts as the sign-out control, completing the session lifecycle in the UI.

---

## Description

On every authenticated page, add a user identity chip to the top-right corner of the navigation bar. The chip displays the user's first name and their assigned market code in parentheses (e.g. `"Shreyas (US)"`). The chip is populated by calling `GET /api/user/me` (PROT-105) on page load.

Clicking the chip opens a small dropdown that contains:
- The user's full name and email as a non-clickable header (for disambiguation).
- A "Sign out" button.

Clicking "Sign out" sends `DELETE /api/session` to end the server-side session, then redirects the browser to the login page (`/login`).

### Chip anatomy
```
[ Shreyas (US) ▾ ]
```
On click, dropdown expands:
```
Shreyas Jagannath
shreyas.jagannath@newpage.io
────────────────────
[ Sign out ]
```

---

## Acceptance Criteria

- AC1: Nav bar shows a chip with the user's first name
- AC2: Chip also shows the user's market in parentheses
- AC3: Chip is fully visible at 1280×800 without overflow
- AC4: Clicking the chip opens a dropdown with a "Sign out" option
- AC5: Clicking "Sign out" calls DELETE /api/session and redirects to /login


**AC1 — Nav bar shows a chip with the user's first name**  
Given a logged-in user named "Shreyas Jagannath",  
When any authenticated page is loaded,  
Then the top-right of the nav bar contains a chip element that shows the text "Shreyas" (first name only, not full name).

**AC2 — Chip also shows the user's market in parentheses**  
Given a logged-in user assigned to the "US" market,  
When an authenticated page is loaded,  
Then the chip text reads "Shreyas (US)" — the market code in parentheses, separated by a space.

**AC3 — Chip is fully visible at 1280×800 without overflow**  
Given a browser window set to 1280×800,  
When any authenticated page is loaded,  
Then the chip element is visible in the top-right of the nav bar, no text is clipped, and there is no horizontal scrollbar on the page.

**AC4 — Clicking the chip opens a dropdown with a "Sign out" option**  
Given the user chip is visible in the nav bar,  
When the user clicks on the chip,  
Then a dropdown appears containing a "Sign out" button that is clickable.

**AC5 — Clicking "Sign out" calls DELETE /api/session and redirects to /login**  
Given the dropdown is open and the user clicks "Sign out",  
When the click is processed,  
Then the browser sends `DELETE /api/session` to the server and the browser URL changes to `/login` (or the root login route).

---

## Edge Cases

- **`/api/user/me` fails or returns 401 on load**: show a generic fallback chip ("Account ▾") and do not crash the page; still show the "Sign out" option.
- **Very long first name** (e.g. "Bartholomew"): truncate with an ellipsis at a reasonable width (e.g. max 16 characters before the market code) rather than pushing layout elements out of the nav.
- **Very long market code** (e.g. "LATAM"): the combined text "Bartholomew (LATAM)" must still fit within the nav bar on a 1280×800 viewport.
- **User's name contains non-ASCII characters** (e.g. "José"): must render correctly without character encoding issues.
- **Dropdown already open, user clicks elsewhere on the page**: the dropdown must close.

---

## Out of Scope
- A user profile edit page or the ability to change name or market from this chip.
- Session expiry warning banner (that is a consumer of `sessionExpiresAt` from PROT-105 and a separate feature).
- Role display in the chip — the chip shows name and market only.

## Dependencies
- PROT-105 (`GET /api/user/me`) provides the user data the chip displays. This endpoint must be available (or mocked) to test the chip fully.
- The `DELETE /api/session` endpoint must exist for AC5 to pass; if not yet built, mock it in the Playwright test.

## Definition of Done
- [ ] User chip visible in nav bar on all authenticated pages
- [ ] Chip text dynamically populated from `GET /api/user/me`
- [ ] All 5 acceptance criteria pass as named Playwright scenarios
- [ ] Overflow and long-name edge cases verified in Playwright
- [ ] The generated Gherkin feature file covers each AC as a distinct scenario
