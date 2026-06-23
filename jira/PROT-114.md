# PROT-114 — Add GET /api/assessments/export endpoint returning CSV stream

**Type**: Story  
**Priority**: Low  
**Epic**: CSV Export  
**Test type**: pytest-bdd  

---

## User Story
As a front-end export button (PROT-113), I need a server endpoint that responds to `GET /api/assessments/export` with a properly formatted, downloadable CSV file containing all of the authenticated user's assessment submissions, so that the browser can save it directly without any client-side data transformation.

## Business Context
The "Export as CSV" button on `/history` (PROT-113) initiates a browser-native download. For this to work reliably, the server must return the correct `Content-Type: text/csv` and `Content-Disposition: attachment; filename="assessments_export.csv"` headers. The browser uses these headers to trigger the save-file dialog. Without correct headers, the browser may display the CSV as raw text in the tab instead of saving it. This endpoint also handles CSV escaping — rationale text often contains commas and quotes, which must be correctly RFC 4180-escaped or the file will corrupt in Excel.

---

## Description

Add a `GET /api/assessments/export` route handler. The endpoint retrieves all of the authenticated user's submissions (no pagination — full dataset), formats them as RFC 4180-compliant CSV, and returns the CSV content with the correct response headers to trigger a browser download.

**Route registration**: this route must be registered before `GET /api/assessments/:id` to avoid the router interpreting `"export"` as an `:id` parameter.

### Response headers
```
Content-Type: text/csv; charset=utf-8
Content-Disposition: attachment; filename="assessments_export.csv"
```

### CSV format
- Header row: `element,task,selfScore,rationale,submittedAt`
- One data row per submission, in `submittedAt` ascending order (oldest first — natural export chronology).
- All fields are comma-separated.
- String fields that contain commas, double-quotes, or newlines must be enclosed in double-quotes per RFC 4180. A double-quote character inside a quoted field is escaped as `""`.

### Example output
```csv
element,task,selfScore,rationale,submittedAt
HCP Engagement,Identify top HCPs,4,Good model in place.,2026-06-01T10:00:00.000Z
Brand Planning,"Plan for H2, including launch",3,"Said ""good"" but needs more work.",2026-06-10T14:30:00.000Z
```

---

## Acceptance Criteria

**AC1 — Response returns HTTP 200 with Content-Type text/csv**  
Given an authenticated user calls `GET /api/assessments/export`,  
When the request is processed,  
Then the server responds with HTTP 200 and the `Content-Type` header is `text/csv; charset=utf-8` (or `text/csv` at minimum).

**AC2 — Response includes Content-Disposition header with correct filename**  
Given an authenticated user calls `GET /api/assessments/export`,  
When the request is processed,  
Then the response headers include `Content-Disposition: attachment; filename="assessments_export.csv"`.

**AC3 — CSV body starts with the correct header row**  
Given any valid request,  
When the response body is inspected,  
Then the first line is exactly: `element,task,selfScore,rationale,submittedAt`.

**AC4 — Rationale fields containing commas are correctly quoted**  
Given a submission whose `rationale` contains a comma (e.g. `"Good model, needs validation"`),  
When the row appears in the CSV output,  
Then the rationale field is enclosed in double-quotes: `"Good model, needs validation"` — so the field does not break into two columns when opened in Excel.

**AC5 — Authenticated user with no submissions receives header-only response with HTTP 200**  
Given an authenticated user has zero submissions,  
When they call `GET /api/assessments/export`,  
Then the server responds with HTTP 200, the correct headers, and a body containing only the header row with no data rows below it.

---

## Edge Cases

- **Rationale containing double-quote characters**: a `"` inside the rationale must be escaped as `""` within the quoted field (RFC 4180 rule).
- **Rationale containing newline characters**: the field must be double-quoted and the newline preserved inside quotes; the CSV parser should not interpret it as a new row.
- **Very large export** (e.g. 1000 submissions): stream the response rather than buffering the entire CSV in memory before sending.
- **Route collision with `:id`**: verify `GET /api/assessments/export` is not matched as `GET /api/assessments/:id` — registration order is critical.
- **Unauthenticated request**: return HTTP 401; do not return any CSV content.

---

## Out of Scope
- Filtering the export by element, date range, or score.
- JSON or XLSX export formats.
- Streaming progress indication on the client.

## Dependencies
- PROT-101 (POST endpoint) must exist to create the submission records being exported.
- PROT-104 (auth middleware) scopes the export to the authenticated user.
- PROT-113 (export button on `/history` page) is the UI consumer of this endpoint.

## Definition of Done
- [ ] Route handler exists at `GET /api/assessments/export` registered before `GET /api/assessments/:id`
- [ ] All 5 acceptance criteria pass as named pytest-bdd scenarios
- [ ] RFC 4180 escaping tested with a rationale containing commas, double-quotes, and a newline
- [ ] Empty-user scenario (header-only response) has an explicit test scenario
- [ ] The generated Gherkin feature file covers each AC as a distinct scenario
