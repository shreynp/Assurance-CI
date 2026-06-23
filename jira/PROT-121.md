# PROT-121 — Add POST /api/notifications to create an in-app alert for a user

**Type**: Story  
**Priority**: Low  
**Epic**: Notifications  
**Test type**: pytest-bdd  

---

## User Story
As a system service or admin, I want to create a persisted notification record for a specific user via an API call, so that in-app alerts (e.g. "Your AI assessment for HCP Engagement is complete", "Your gate is now RED") are stored server-side and surfaced to the user the next time they poll or load the notification bell.

## Business Context
System events like an AI assessment completing or a gate status changing to RED need to reach the contributor without requiring them to manually refresh the page. An in-app notification system serves as the delivery mechanism. This endpoint is the write side: it creates a persisted notification record that the notification bell (PROT-122) polls for. The endpoint is restricted to admins and internal service tokens to prevent contributors from creating notifications for other users.

---

## Description

Add a `POST /api/notifications` route handler. The endpoint creates a new notification record for the specified `userId`, persists it to the data store, and returns the created record. The endpoint is restricted: only admin-role users or requests bearing an internal service token may call it. Contributor tokens receive 403.

### Request payload (JSON body)
```json
{
  "userId": "user_abc123",
  "type": "ai_complete",
  "message": "Your AI assessment for HCP Engagement is complete.",
  "link": "/triangulated?assessmentId=assess_01J2XKPQ3W"
}
```

`link` is optional. When provided, the notification bell renders it as a clickable link. `type` is a free-form string identifier (e.g. `"ai_complete"`, `"gate_red"`, `"gate_green"`, `"system"`) — the API does not validate against a fixed enum in this prototype.

### Success response (HTTP 201)
```json
{
  "id": "notif_01J2XKPQ3W",
  "userId": "user_abc123",
  "type": "ai_complete",
  "message": "Your AI assessment for HCP Engagement is complete.",
  "link": "/triangulated?assessmentId=assess_01J2XKPQ3W",
  "read": false,
  "readAt": null,
  "createdAt": "2026-06-23T15:00:00.000Z"
}
```

`read` defaults to `false`. `readAt` is `null` until the notification is marked read via PROT-123. `createdAt` is the server timestamp at the moment of creation.

---

## Acceptance Criteria

**AC1 — Valid request returns 201 with the created notification record**  
Given an admin user sends `POST /api/notifications` with `userId: "user_abc123"`, `type: "ai_complete"`, `message: "AI done"`, and `link: "/triangulated"`,  
When the request is processed,  
Then the server responds with HTTP 201 and a JSON body containing all submitted fields plus `id`, `read: false`, `readAt: null`, and `createdAt`.

**AC2 — Response includes all required fields in the correct shape**  
Given a valid notification creation request,  
When the server responds,  
Then the body includes `id` (string), `userId`, `type`, `message`, `link` (or `null` if not sent), `read: false`, `readAt: null`, and `createdAt` (ISO-8601 UTC timestamp).

**AC3 — `read` defaults to false on creation**  
Given any valid notification creation request,  
When the notification record is created,  
Then `read` is `false` in the response body — it must never be `true` for a newly created notification.

**AC4 — Missing userId or message returns 400**  
Given an admin sends `POST /api/notifications` with `message` but no `userId`,  
When the request is processed,  
Then the server responds with HTTP 400 and an error identifying `userId` as the missing field.

Given an admin sends `POST /api/notifications` with `userId` but no `message`,  
When the request is processed,  
Then the server responds with HTTP 400 and an error identifying `message` as the missing field.

**AC5 — Contributor token returns 403**  
Given a user with `role: "contributor"` sends `POST /api/notifications` with a valid payload,  
When the request is processed,  
Then the server responds with HTTP 403 and no notification record is created.

---

## Edge Cases

- **`link` omitted**: create the notification successfully; `link` field in the response is `null` (not absent).
- **`userId` refers to a non-existent user**: return HTTP 404 (`{ "error": "User not found" }`) — do not create a notification for an unknown user.
- **`message` is an empty string**: return HTTP 400; message must be non-empty.
- **`message` exceeds 500 characters**: return HTTP 400 with the error "message must be 500 characters or fewer".
- **Internal service token** (if applicable): treated as equivalent to admin for this endpoint — returns 201 on valid payload.

---

## Out of Scope
- Sending push notifications or emails — this is in-app only.
- Notification type validation against a fixed enum — `type` is a free-form string in this prototype.
- Bulk notification creation (one payload = one notification).

## Dependencies
- PROT-104 (auth middleware) validates the Bearer token and resolves the caller's role.
- PROT-122 (notification bell) is the primary consumer of the notifications created here.
- PROT-123 (mark as read) updates the `read` / `readAt` fields on records created here.

## Definition of Done
- [ ] Route handler exists at `POST /api/notifications`
- [ ] All 5 acceptance criteria pass as named pytest-bdd scenarios
- [ ] Missing `userId` and missing `message` each have distinct test scenarios
- [ ] 403 for contributor role has an explicit test scenario
- [ ] The generated Gherkin feature file covers each AC as a distinct scenario
