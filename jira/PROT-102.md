# PROT-102 — Replace self-assessment numeric input with a range slider

**Type**: Story  
**Priority**: Medium  
**Epic**: Assessment UX  
**Test type**: Playwright  

---

## User Story
As a market contributor completing a self-assessment, I want to set my score using a slider rather than typing a number, so that the scoring gesture feels deliberate and the selected value is always visually clear as I position it.

## Business Context
The current number input (`<input type="number" min="1" max="5">`) requires the user to type a value, provides no spatial sense of where they sit on the scale, and is trivially misconfigured (typing "55" is not blocked until submission). Assessments are scored 1–5 — five discrete positions that map perfectly to a horizontal drag. The slider makes the scoring feel like a considered positioning act rather than data entry, reduces input errors, and makes the selected value impossible to misread. This is a pure UX improvement; it does not change the API payload or any stored value.

---

## Description

On the `/assessment` page, replace the `<input type="number">` element used for self-score entry with an `<input type="range">` slider. The slider must:

- Snap to exactly five discrete positions: 1, 2, 3, 4, 5.
- Display the currently selected integer value in a visible label adjacent to (or below) the slider handle, updating in real time as the user drags — not only on release.
- Default to position **3** when the form first loads (representing a neutral mid-point).
- Submit the same integer value that a number input would have sent; the `POST /api/assessments` payload and API contract are unchanged.
- Be keyboard-accessible: arrow keys should advance or retreat the handle one step.

### Visual layout (conceptual)
```
Score
  1 ——————●—————————— 5
          3              ← label shows current value, updates while dragging
```

The track spans the full width of the form field. Labels "1" and "5" appear at the extreme ends for orientation. The live-value label floats above or below the handle.

---

## Acceptance Criteria

- AC1: Slider renders in place of the numeric input
- AC2: Live label updates during drag, not only on release
- AC3: Slider only stops at integer positions 1 through 5
- AC4: Form submission includes the slider's integer value in the request body
- AC5: Full slider track is visible at 1280×800 without clipping
- AC6: Page load defaults to position 3


**AC1 — Slider renders in place of the numeric input**  
Given a user navigates to `/assessment`,  
When the page fully loads,  
Then the self-score field contains an `<input type="range" min="1" max="5" step="1">` element and no `<input type="number">` element is present in the DOM.

**AC2 — Live label updates during drag, not only on release**  
Given the slider handle is at position 3,  
When the user drags the handle toward position 5 (Playwright: use `dragTo` or `dispatchEvent`),  
Then the adjacent score label reads the intermediate value during the drag (e.g. "4") before the mouse button is released.

**AC3 — Slider only stops at integer positions 1 through 5**  
Given the slider is rendered with `step="1"` `min="1"` `max="5"`,  
When the user interacts with it,  
Then the slider value attribute is always one of `1`, `2`, `3`, `4`, `5` — never a decimal or a value outside that range.

**AC4 — Form submission includes the slider's integer value in the request body**  
Given the slider is positioned at 4,  
When the user clicks "Submit" and the form is submitted,  
Then the HTTP request body to `POST /api/assessments` contains `"selfScore": 4` as a JSON integer (not a string, not a decimal).

**AC5 — Full slider track is visible at 1280×800 without clipping**  
Given a browser window set to 1280×800,  
When the `/assessment` page is loaded,  
Then the entire slider track from position 1 to position 5 and the live-value label are visible on screen without any part being obscured or scrolled out of view.

**AC6 — Page load defaults to position 3**  
Given the user opens `/assessment` for the first time in a session (no prior submission in this form load),  
When the page finishes rendering,  
Then the slider handle is at position 3 and the score label reads "3".

---

## Edge Cases

- **Keyboard navigation at boundary**: pressing ArrowRight on a focused slider at position 5 must not advance beyond 5; pressing ArrowLeft at position 1 must not go below 1. (Browser enforces this via `max`/`min` — Playwright test should assert boundary behaviour.)
- **Mobile / touch**: the slider must respond to touch drag on a touch-enabled device. Secondary test at 390×844 viewport (iPhone 14 logical size).
- **Form reset**: if the user resets the form (e.g. a "Clear" button, if present), the slider must return to default position 3.
- **Pre-populated edit mode**: if the form is pre-loaded with an existing submission's score (e.g. from PROT-107 edit flow), the slider must initialise to that score, not the default 3.

---

## Out of Scope
- Descriptive labels per step (e.g. "Poor", "Excellent") — integers only in this ticket.
- Changing the 1–5 scale — fixed by the API contract in PROT-101.
- Any change to the API payload structure.

## Dependencies
- No blocking dependency; buildable and testable against the existing form independently of PROT-101.
- The form's submit handler must pass the slider's integer value to the API — verify integration once PROT-101 is merged.

## Definition of Done
- [ ] `<input type="number">` removed from the self-score field on `/assessment`
- [ ] `<input type="range" min="1" max="5" step="1">` present in its place
- [ ] Live label updates confirmed in Playwright by asserting DOM text value mid-interaction
- [ ] All 6 acceptance criteria pass as named Playwright scenarios
- [ ] The generated Gherkin feature file covers each AC as a distinct scenario
