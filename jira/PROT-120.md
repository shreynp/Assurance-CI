# PROT-120 — Add role guard redirecting non-admin users away from /admin

**Type**: UI story
**Test type**: Playwright

## Description
The /admin page is currently accessible to any authenticated user. Add client-side and server-side guards so that non-admin users who navigate to /admin are immediately redirected to /assessment with an explanatory message.

## Acceptance Criteria
- AC1: A logged-in contributor navigating to /admin is redirected to /assessment
- AC2: After the redirect a toast message appears: "You do not have permission to access the admin area"
- AC3: The redirect happens before any admin data is fetched or rendered
- AC4: A logged-in admin user can access /admin without any redirect
- AC5: An unauthenticated user navigating to /admin is redirected to the login page
