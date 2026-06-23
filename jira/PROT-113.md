# PROT-113 — Add "Export as CSV" button on the /history page

**Type**: Story  
**Priority**: Low  
**Epic**: CSV Export  
**Test type**: Playwright  

---

## User Story
As a market contributor or manager, I want to download all my assessment submissions as a CSV file from the history page, so that I can share the data with regional stakeholders or import it into a spreadsheet for further analysis without needing API access.

## Business Context
Market managers need to share assessment data with regional stakeholders in spreadsheet format for quarterly business reviews and line-manager check-ins. Currently all data lives behind the app UI with no offline extraction path. A single "Export as CSV" button on the history page provides a zero-friction extraction mechanism. The button calls the `GET /api/assessments/export` endpoint (PROT-114) which handles the actual CSV generation — this ticket is purely the UI trigger and download initiation.

---

## Description

Add an "Export as CSV" button to the `/history` page, placed prominently above the assessment table (or in the page header actions area). Clicking the button initiates a file download by navigating to `GET /api/assessments/export`. The browser should save the file as `assessments_export.csv`.

The button must always be visible, even when the user has no submissions — in that case the downloaded file will contain only the header row (the API handles this correctly per PROT-114).

### Button placement
Top-right of the history page, aligned with the page header. A secondary label "Download all submissions" can appear as a subtitle or tooltip.

### Download mechanism
Use `window.location.href = '/api/assessments/export'` or a `<a href="/api/assessments/export" download>` anchor to initiate the download. Do not use `fetch` + `Blob` — the server sends `Content-Disposition: attachment` which the browser handles natively.

---

## Acceptance Criteria

**AC1 — "Export as CSV" button is visible on the /history page**  
Given a user navigates to `/history`,  
When the page loads (regardless of whether there are submissions),  
Then a button or link with the text "Export as CSV" is visible on the page.

**AC2 — Clicking the button triggers a file download named assessments_export.csv**  
Given the user clicks "Export as CSV",  
When the browser processes the click,  
Then a file download is initiated and the browser saves (or prompts to save) a file with the name `assessments_export.csv`. (Playwright: verify via `page.waitForEvent('download')` and assert the suggested filename.)

**AC3 — The downloaded file contains a header row with the correct column names**  
Given the download completes,  
When the CSV content is inspected,  
Then the first line reads: `Element,Task,Self Score,Rationale,Submitted At` (exact column names, comma-separated).

**AC4 — Each submission appears as a data row in the correct column order**  
Given the user has 2 submissions,  
When the CSV is downloaded,  
Then the file contains 3 lines total: 1 header row + 2 data rows, each row having values in the order: Element, Task, Self Score, Rationale, Submitted At.

**AC5 — Button is still visible and clickable when the user has no submissions**  
Given the authenticated user has zero submissions,  
When they navigate to `/history` and click "Export as CSV",  
Then a CSV file is downloaded that contains only the header row and no data rows.

---

## Edge Cases

- **Button disabled state**: the button should never be disabled — even with zero submissions, the export is valid (header-only file).
- **Concurrent click**: if the user double-clicks the button, only one download is initiated — debounce the click handler.
- **API error on export** (e.g. 500): show an inline error message ("Export failed. Please try again.") rather than silently ignoring the failure.
- **Very large dataset**: the button should not show a loading spinner that blocks the UI — the browser handles the download natively; once the `<a>` is clicked the UI is free.

---

## Out of Scope
- Filtering the export by date range or element — always exports all submissions.
- Export formats other than CSV.
- The server-side CSV generation logic — see PROT-114.

## Dependencies
- PROT-114 (`GET /api/assessments/export`) is the API endpoint this button calls; it must be available for AC2–AC5 to pass.
- PROT-109 (`/history` page) must exist as the host page.

## Definition of Done
- [ ] "Export as CSV" button visible on `/history` page
- [ ] Playwright `waitForEvent('download')` confirms filename `assessments_export.csv`
- [ ] All 5 acceptance criteria pass as named Playwright scenarios
- [ ] Zero-submission export scenario has explicit test coverage
- [ ] The generated Gherkin feature file covers each AC as a distinct scenario
