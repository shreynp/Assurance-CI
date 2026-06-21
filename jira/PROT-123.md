# PROT-123 — Add POST /api/notifications/:id/read to mark a notification as read

**Type**: API story
**Test type**: pytest-bdd

## Description
The notification bell needs a reliable API call to persist the read state after the user dismisses an alert. Add an endpoint that marks a specific notification as read and returns the updated record.

## Acceptance Criteria
- AC1: POST /api/notifications/:id/read returns 200 with the notification record where `read` is `true` and `readAt` is set to the current timestamp
- AC2: Calling the endpoint on an already-read notification returns 200 with the existing `readAt` value unchanged
- AC3: A request for a notification that belongs to a different user returns 403
- AC4: A request for a non-existent notification ID returns 404
- AC5: After marking as read, GET /api/notifications returns that notification with `read: true` in subsequent calls
