# PROT-112 — Add completeness progress ring showing how many elements have been scored

**Type**: Story  
**Priority**: Medium  
**Epic**: Analytics  
**Test type**: Playwright  

---

## User Story
As a market contributor on the assessment page, I want to see a progress ring showing how many of the five elements I have scored at least once, so that I can track my completeness at a glance and know immediately when I have finished the full assessment framework.

## Business Context
The assessment framework has five elements (HCP Engagement, Brand Planning, Campaign Execution, Patient Identification, Media & Promotion). Contributors should complete a self-assessment for all five. Currently there is no indicator on the assessment page of how far through the framework a contributor is — they must check the history page or count from memory. A progress ring in the top section of the `/assessment` page provides an immediate, at-a-glance completeness signal. It updates after each successful submission without requiring a page reload, giving the contributor real-time feedback and a clear "done" state when all five are scored.

---

## Description

Add a circular progress ring widget to the top section of the `/assessment` page. The ring is populated from `GET /api/assessments/summary` (PROT-110), which returns which elements have at least one submission (`submissionCount > 0`). The ring shows `X of 5 elements scored`.

### Ring states
| Condition | Ring fill | Ring colour | Label |
|-----------|-----------|-------------|-------|
| 0 elements scored | 0% | Blue (`#005BAB`) | "0 of 5 elements scored" |
| 1–4 elements scored | 20–80% | Blue (`#005BAB`) | "N of 5 elements scored" |
| All 5 elements scored | 100% | Green (`#137B4D`) | "5 of 5 elements scored" |

The ring fill is proportional: 1 element = 20%, 2 = 40%, 3 = 60%, 4 = 80%, 5 = 100%.

### Live update behaviour
After a successful `POST /api/assessments` submission (PROT-101), the ring must update its count without a full page reload. The page re-calls `GET /api/assessments/summary` and re-renders the ring with the new count.

---

## Acceptance Criteria

**AC1 — Completeness ring is visible in the top section of /assessment**  
Given a user navigates to `/assessment`,  
When the page loads,  
Then a circular progress ring element is visible in the upper portion of the page above the assessment form, showing the text "X of 5 elements scored".

**AC2 — Ring fill is proportional to the fraction of scored elements**  
Given a user has scored 3 of the 5 elements,  
When the ring renders,  
Then the ring arc is filled to 60% of its circumference and the label reads "3 of 5 elements scored".

**AC3 — Ring turns green and fills completely when all 5 elements are scored**  
Given a user has scored all 5 elements (each has `submissionCount > 0` in the summary),  
When the ring renders,  
Then the ring arc is filled to 100%, its colour changes to green (`#137B4D`), and the label reads "5 of 5 elements scored".

**AC4 — Ring count updates immediately after a successful submission, without a page reload**  
Given a user has scored 2 of 5 elements and the ring shows "2 of 5 elements scored",  
When they submit a valid assessment for a third, previously unscored element,  
Then the ring updates to "3 of 5 elements scored" and the arc fills to 60% without the browser reloading the page.

**AC5 — Ring is visible at 1280×800 viewport in the top section of the page**  
Given a browser window set to 1280×800,  
When the `/assessment` page is loaded,  
Then the progress ring is visible in the viewport without requiring any scrolling.

---

## Edge Cases

- **0 elements scored** (brand new user): ring renders with 0% fill and label "0 of 5 elements scored" — not hidden.
- **Multiple submissions for the same element**: submitting the same element a second time does not increase the count — an element is scored once it has `submissionCount ≥ 1`, regardless of how many submissions exist for it.
- **`GET /api/assessments/summary` returns an error on load**: render the ring at 0/5 with a subtle error indicator; do not crash the page or block the assessment form.
- **Submission fails (API returns 400)**: the ring does not increment; the count only updates on successful 200 responses from `POST /api/assessments`.

---

## Out of Scope
- Showing which specific elements are scored vs. not scored (that detail is on the history page).
- An animated celebration when the ring completes to 100% — static colour change only.
- Progress rings for tasks within an element.

## Dependencies
- PROT-110 (`GET /api/assessments/summary`) provides the per-element submission counts.
- PROT-101 (POST endpoint) must succeed for the live-update behaviour (AC4) to trigger.

## Definition of Done
- [ ] Circular progress ring visible on `/assessment` page
- [ ] Ring fills proportionally for 0–5 scored elements
- [ ] Colour change to green at 5/5 verified in Playwright
- [ ] Live update on submission (AC4) tested without page reload in Playwright
- [ ] All 5 acceptance criteria pass as named Playwright scenarios
- [ ] The generated Gherkin feature file covers each AC as a distinct scenario
