# PROT-122 — Show notification bell icon with unread count badge in the nav

**Type**: UI story
**Test type**: Playwright

## Description
Users have no awareness of in-app notifications unless they navigate to a dedicated page. Add a bell icon to the nav bar that shows a badge with the count of unread notifications, polling GET /api/notifications every 30 seconds.

## Acceptance Criteria
- AC1: A bell icon appears in the nav bar on all authenticated pages
- AC2: When there are unread notifications a badge displays the unread count on the bell icon
- AC3: When all notifications are read the badge disappears
- AC4: Clicking the bell icon opens a dropdown listing the five most recent notifications with message and timestamp
- AC5: Each notification in the dropdown includes a "Mark as read" action that updates the badge count immediately
