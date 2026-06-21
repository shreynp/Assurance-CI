# PROT-113 — Add "Export as CSV" button on the /history page

**Type**: UI story
**Test type**: Playwright

## Description
Market managers need to share assessment data with regional stakeholders in spreadsheet format. Add a button on /history that triggers a CSV download of all the user's submissions via GET /api/assessments/export.

## Acceptance Criteria
- AC1: An "Export as CSV" button is visible on the /history page
- AC2: Clicking the button triggers a file download named `assessments_export.csv`
- AC3: The downloaded file contains a header row: Element, Task, Self Score, Rationale, Submitted At
- AC4: Each submission appears as one row in the correct column order
- AC5: If there are no submissions the button is still present but the downloaded file contains only the header row
