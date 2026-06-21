# PROT-106 — Show logged-in user name and market in the nav header

**Type**: UI story
**Test type**: Playwright

## Description
After login the user has no visual confirmation of who they are or which market they are operating in. Add a user chip in the top-right of the nav bar that shows the user's first name and their assigned market, pulling from /api/user/me.

## Acceptance Criteria
- AC1: The nav bar on all authenticated pages shows a chip with the user's first name
- AC2: The chip also shows the user's market in parentheses, e.g. "Shreyas (US)"
- AC3: The chip is visible on a 1280×800 viewport without any horizontal overflow
- AC4: Clicking the chip opens a small dropdown with a "Sign out" option
- AC5: Clicking "Sign out" calls DELETE /api/session and redirects to the login page
