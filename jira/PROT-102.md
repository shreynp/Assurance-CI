# PROT-102 — Replace self-assessment numeric input with a range slider

**Type**: UI story
**Test type**: Playwright

## Description
The current self-assessment uses a plain number input box (1–5). Replace it with a styled range slider that shows the current value live as the user drags, making the scoring more intuitive.

## Acceptance Criteria
- AC1: A slider replaces the numeric input on the /assessment page
- AC2: Dragging the slider updates the displayed score value in real time
- AC3: The slider only allows values 1, 2, 3, 4, 5 (discrete steps)
- AC4: Submitting the form sends the same score value as the slider position
- AC5: The slider is visible and usable on a 1280×800 viewport
