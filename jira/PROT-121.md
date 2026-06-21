# PROT-121 — Add POST /api/notifications to create an in-app alert for a user

**Type**: API story
**Test type**: pytest-bdd

## Description
System events (e.g. an AI assessment completing, a gate turning RED) need to surface as in-app alerts without requiring the user to refresh. Add a notifications endpoint that creates a persisted alert record for a specified user.

## Acceptance Criteria
- AC1: POST /api/notifications with `userId`, `type`, `message`, and optional `link` fields returns 201 with the created notification record
- AC2: The response includes `id`, `userId`, `type`, `message`, `link`, `read`, and `createdAt` fields
- AC3: `read` defaults to `false` on creation
- AC4: A request missing `userId` or `message` returns 400
- AC5: Only authenticated admin users or internal service tokens may call this endpoint; contributor tokens return 403
