# PROT-117 — Add confidence score badge next to each data source label on /triangulated

**Type**: UI story
**Test type**: Playwright

## Description
The spider chart shows three overlapping series (Self, AI, ICO) but gives no indication of how reliable each score is. Add a small confidence badge next to each series label in the legend, sourced from the triangulation API response.

## Acceptance Criteria
- AC1: Each series label in the spider chart legend has a confidence badge showing a percentage (e.g. "AI Score 87%")
- AC2: Badges above 80% are styled in green; 50–79% in amber; below 50% in red
- AC3: Hovering over a confidence badge shows a tooltip explaining what the score represents
- AC4: If confidence data is unavailable for a source, the badge shows "—" instead of a percentage
- AC5: Badges are visible at the 1280×800 viewport without overlapping chart elements
