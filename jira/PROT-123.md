# PROT-123 — Add POST /api/notifications/:id/read to mark a notification as read

**Type**: Story  
**Priority**: Low  
**Epic**: Notifications  
**Test type**: pytest-bdd  

---

## User Story
As a contributor or admin who has acknowledged an in-app notification, I want the read state to be persisted server-side when I click "Mark as read", so that the notification badge count decrements and the notification does not re-appear as unread after the next poll or page reload.

## Business Context
The notification bell (PROT-122) shows an unread count badge and a "Mark as read" button on each notification item. When the user clicks "Mark as read", the client needs a reliable API call to persist the read state. Without server-side persistence, the badge would revert to the original unread count on the next 30-second poll or page reload, making the "Mark as read" action feel broken. This endpoint also ensures idempotency: calling it on an already-read notification is safe — it returns the existing record unchanged rather than throwing an error.

---

## Description

Add a `POST /api/notifications/:id/read` route handler. The endpoint marks the specified notification as read by setting `read: true` and `readAt` to the current server time, then returns the full updated notification record. The endpoint enforces ownership: a user can only mark their own notifications as read.

### Why POST not PATCH?
This is a state-transition endpoint (unread → read), not a general-purpose partial update. Using POST for a semantically distinct action (rather than PATCH on the notification resource) keeps the API intent explicit and makes it easy to generate a typed SDK method `markNotificationRead(id)`.

### Success response (HTTP 200)
```json
{
  "id": "notif_01J2XKPQ3W",
  "userId": "user_abc123",
  "type": "ai_complete",
  "message": "Your AI assessment for HCP Engagement is complete.",
  "link": "/triangulated?assessmentId=assess_01J2XKPQ3W",
  "read": true,
  "readAt": "2026-06-23T15:05:00.000Z",
  "createdAt": "2026-06-23T15:00:00.000Z"
}
```

`read` is `true`. `readAt` is the server timestamp at the moment the read was first recorded. `createdAt` is the original creation timestamp — unchanged.

---

## Acceptance Criteria

**AC1 — Marking an unread notification returns 200 with read: true and readAt set**  
Given notification `notif_01J2XKPQ3W` exists with `read: false` and belongs to the authenticated user,  
When they send `POST /api/notifications/notif_01J2XKPQ3W/read`,  
Then the server responds with HTTP 200 and the response body contains `read: true` and a `readAt` ISO-8601 UTC timestamp.

**AC2 — Calling the endpoint on an already-read notification is idempotent**  
Given notification `notif_01J2XKPQ3W` is already `read: true` with `readAt: "2026-06-23T15:05:00.000Z"`,  
When the user calls `POST /api/notifications/notif_01J2XKPQ3W/read` a second time,  
Then the server responds with HTTP 200 and the `readAt` value in the response is still `"2026-06-23T15:05:00.000Z"` — the timestamp is not overwritten.

**AC3 — Marking a notification belonging to a different user returns 403**  
Given notification `notif_B1` belongs to user B and user A is authenticated,  
When user A calls `POST /api/notifications/notif_B1/read`,  
Then the server responds with HTTP 403 and the notification is not modified.

**AC4 — Non-existent notification ID returns 404**  
Given an authenticated user calls `POST /api/notifications/notif_DOESNOTEXIST/read`,  
When the request is processed,  
Then the server responds with HTTP 404.

**AC5 — After marking as read, GET /api/notifications reflects the updated state**  
Given the user has marked notification `notif_01J2XKPQ3W` as read,  
When they subsequently call `GET /api/notifications`,  
Then the notification appears in the response with `read: true` and the `unreadCount` is decremented by 1 compared to before the mark-read action.

---

## Edge Cases

- **Concurrent mark-read calls for the same notification**: both succeed with 200; `readAt` is set to whichever server timestamp was recorded first (last-writer-wins on the timestamp is acceptable — both agree the notification is read).
- **Unauthenticated request**: return HTTP 401 before any data is read or modified.
- **`notif_INVALID` format ID** (not matching the expected ID format): return HTTP 404 — treat unrecognised IDs the same as non-existent ones; do not expose ID format details.
- **`readAt` immutability after first mark**: calling the endpoint a third time must still return the original `readAt` from the first successful mark — it is never overwritten.

---

## Out of Scope
- Bulk mark-all-as-read — one notification per call.
- Marking a notification as unread (reverting `read: true` back to `false`).
- Deleting notifications.

## Dependencies
- PROT-121 (`POST /api/notifications`) creates the notification records this endpoint operates on.
- PROT-104 (auth middleware) provides the authenticated user context for ownership validation.
- PROT-122 (notification bell) calls this endpoint when the user clicks "Mark as read".

## Definition of Done
- [ ] Route handler exists at `POST /api/notifications/:id/read`
- [ ] All 5 acceptance criteria pass as named pytest-bdd scenarios
- [ ] Idempotency (AC2) verified: `readAt` does not change on second call
- [ ] 403 ownership enforcement verified with a two-user test fixture
- [ ] AC5 (GET reflects updated state after mark-read) has an explicit end-to-end scenario
- [ ] The generated Gherkin feature file covers each AC as a distinct scenario
