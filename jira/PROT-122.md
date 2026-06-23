# PROT-122 — Show notification bell icon with unread count badge in the nav

**Type**: Story  
**Priority**: Low  
**Epic**: Notifications  
**Test type**: Playwright  

---

## User Story
As a logged-in contributor or admin, I want to see a notification bell in the navigation bar that shows how many unread alerts I have, so that I am aware of system events (AI assessment completions, gate status changes) without having to navigate to a separate page or manually refresh.

## Business Context
Contributors and admins receive in-app notifications when important system events occur (e.g. "Your AI assessment for HCP Engagement is complete"). Without a visible indicator in the nav bar, these notifications go unnoticed unless the user actively checks a notifications page. A bell icon with an unread count badge — a ubiquitous pattern — surfaces this information passively while the user is working in any part of the app. The badge disappears when everything is read, so it does not become noise once acknowledged.

---

## Description

Add a notification bell icon to the navigation bar on all authenticated pages. The bell shows a count badge for unread notifications. The badge is populated by calling `GET /api/notifications` on page load and then polling every 30 seconds.

### Notification bell anatomy
```
Nav bar:  [Logo]  [Assessment]  [History]  [Triangulated]    [🔔 3]  [Shreyas (US) ▾]
```
The badge is a circular chip overlaid on the top-right corner of the bell icon, showing the unread count (integer). When unread count is 0 the badge is not rendered (not a "0" badge — it disappears entirely).

### Dropdown (on bell click)
Clicking the bell opens a dropdown listing the **5 most recent notifications** (regardless of read status), ordered by `createdAt` descending. Each item shows:
- **Message text**
- **Timestamp** (relative: "2 minutes ago", "1 hour ago"; or absolute if older than 24 hours: "23 Jun 2026")
- **"Mark as read" button** (only visible if `read: false`)
- If `link` is set: the message text is a clickable link

### Polling
`GET /api/notifications` is called every 30 seconds. The badge count updates on each poll. The dropdown content updates on each poll while it is open.

### `GET /api/notifications` response shape (expected)
```json
{
  "unreadCount": 3,
  "notifications": [
    {
      "id": "notif_01J2XKPQ3W",
      "type": "ai_complete",
      "message": "Your AI assessment for HCP Engagement is complete.",
      "link": "/triangulated?assessmentId=assess_01J2XKPQ3W",
      "read": false,
      "createdAt": "2026-06-23T15:00:00.000Z"
    }
  ]
}
```

---

## Acceptance Criteria

- AC1: Bell icon appears in nav bar on all authenticated pages
- AC2: Badge shows unread count when there are unread notifications
- AC3: Badge disappears when all notifications are read
- AC4: Clicking the bell opens a dropdown with the 5 most recent notifications
- AC5: Each unread notification in the dropdown has a "Mark as read" action that updates the badge immediately


**AC1 — Bell icon appears in nav bar on all authenticated pages**  
Given a logged-in user is on any authenticated page (`/assessment`, `/history`, `/triangulated`),  
When the page loads,  
Then a bell icon is visible in the navigation bar.

**AC2 — Badge shows unread count when there are unread notifications**  
Given the authenticated user has 3 unread notifications,  
When the page loads or the next poll completes,  
Then a badge is visible on the bell icon showing the number "3".

**AC3 — Badge disappears when all notifications are read**  
Given the user had 1 unread notification and then marks it as read,  
When the next poll completes (or the read action triggers an immediate count update),  
Then the badge is no longer visible on the bell icon.

**AC4 — Clicking the bell opens a dropdown with the 5 most recent notifications**  
Given the user has 7 notifications (3 unread, 4 read),  
When they click the bell icon,  
Then a dropdown appears showing exactly 5 notification items (the 5 most recent by `createdAt`), each displaying the message text and a relative or absolute timestamp.

**AC5 — Each unread notification in the dropdown has a "Mark as read" action that updates the badge immediately**  
Given an unread notification is visible in the dropdown,  
When the user clicks "Mark as read" on that notification,  
Then a `POST /api/notifications/:id/read` request is sent (PROT-123), the badge count decrements by 1 immediately (optimistic update), and the "Mark as read" button disappears from that notification item.

---

## Edge Cases

- **Zero unread notifications on page load**: bell icon renders normally; no badge is shown; dropdown still opens and shows the 5 most recent notifications (all read).
- **No notifications at all**: bell icon renders; dropdown opens and shows an empty-state message "No notifications yet."
- **Unread count > 99**: display "99+" on the badge rather than the raw number to avoid badge overflow.
- **Poll while dropdown is open**: if the dropdown is open during a poll, update the dropdown contents (prepend any new notifications) without closing it.
- **Network error during poll**: do not show an error toast; silently retry on the next 30-second tick. The last known count remains in the badge.
- **Clicking a notification with a `link`**: close the dropdown and navigate to the `link` URL. Mark the notification as read.

---

## Out of Scope
- A dedicated `/notifications` page — the dropdown is the only UI surface in this ticket.
- Browser push notifications — in-app polling only.
- Notification preferences or opt-out.

## Dependencies
- `GET /api/notifications` endpoint (not in the ticketed backlog — assume it exists or create it as part of this ticket as a simple list endpoint).
- PROT-123 (`POST /api/notifications/:id/read`) handles the "Mark as read" action.
- PROT-121 (`POST /api/notifications`) creates the notifications that appear here.

## Definition of Done
- [ ] Bell icon visible in nav bar on all authenticated pages
- [ ] Badge renders with unread count and disappears when count is 0
- [ ] Dropdown shows 5 most recent notifications on bell click
- [ ] "Mark as read" decrements badge count optimistically
- [ ] All 5 acceptance criteria pass as named Playwright scenarios
- [ ] The generated Gherkin feature file covers each AC as a distinct scenario
