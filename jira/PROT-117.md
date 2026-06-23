# PROT-117 — Add confidence score badge next to each data source label on /triangulated

**Type**: Story  
**Priority**: Low  
**Epic**: Triangulation Enhancements  
**Test type**: Playwright  

---

## User Story
As a market contributor reading the triangulated spider chart, I want to see a confidence percentage badge next to each score source label in the legend, so that I understand how reliable each series is — and do not mistake a low-confidence AI score for an authoritative assessment.

## Business Context
The spider chart shows three series (Self, AI, ICO) as if they are equally weighted. In practice they are not: the AI score is an algorithmic estimate with a confidence level, and the ICO benchmark may have higher or lower applicability to a given market. Without a confidence signal, contributors may over-rely on a low-confidence AI score or dismiss a high-confidence ICO benchmark. Showing "AI Score 87%" vs "AI Score 42%" in the legend gives the reader the context they need to weight each series appropriately. The `confidences` object is already returned by the triangulation endpoint (PROT-115) — this ticket is purely a UI addition.

---

## Description

In the spider chart legend on `/triangulated`, add a small badge next to each series label. The badge displays the confidence as a percentage (e.g. `87%`). The confidence values come from the `confidences` object in the `GET /api/assessments/:id/triangulation` response (PROT-115).

### Series and their confidence sources
| Series label | Confidence key | Notes |
|--------------|---------------|-------|
| Self | `confidences.self` | Always `null` — contributor self-scores have no algorithmic confidence |
| AI Score | `confidences.ai` | Float 0.0–1.0, displayed as `Math.round(value * 100)%` |
| ICO Benchmark | `confidences.ico` | Float 0.0–1.0, displayed as percentage |

When `confidence` is `null` or absent for a source, the badge displays `—` instead of a percentage.

### Badge colour thresholds
| Confidence | Badge background/text |
|-----------|----------------------|
| ≥ 80% | Green — `#137B4D` background tint, `#137B4D` text |
| 50–79% | Amber — `#D4820A` background tint, `#D4820A` text |
| < 50% | Red — `#C0392B` background tint, `#C0392B` text |
| `—` (null) | Muted grey — `#6B7D96` |

### Tooltip on hover
Each badge has a hover tooltip explaining the confidence score:
- AI Score: `"AI confidence: the model's reliability score for this element estimate"`
- ICO Benchmark: `"ICO confidence: the benchmark's applicability score for this market"`
- Self: `"Self-assessment scores do not have an algorithmic confidence measure"`

---

## Acceptance Criteria

**AC1 — Each legend label has a confidence badge showing a percentage or "—"**  
Given the `/triangulated` page is loaded for an assessment where `confidences.ai = 0.87` and `confidences.ico = 0.95`,  
When the spider chart legend renders,  
Then the "AI Score" label has a badge reading "87%" and the "ICO Benchmark" label has a badge reading "95%", and the "Self" label has a badge reading "—".

**AC2 — Badge colour reflects confidence level**  
Given `confidences.ai = 0.87` (≥ 80%),  
When the AI Score badge renders,  
Then its background/text colour uses the green style (`#137B4D`).

Given `confidences.ai = 0.60` (50–79%),  
When the AI Score badge renders,  
Then it uses the amber style (`#D4820A`).

Given `confidences.ai = 0.40` (< 50%),  
When the AI Score badge renders,  
Then it uses the red style (`#C0392B`).

**AC3 — Hovering over a confidence badge shows an explanatory tooltip**  
Given the "AI Score" badge is visible in the legend,  
When the user hovers over it,  
Then a tooltip appears containing a description of what the confidence score represents (must include the word "confidence" or "reliability").

**AC4 — Badge shows "—" when confidence data is unavailable for a source**  
Given `confidences.ai = null` (AI confidence not computed for this assessment),  
When the "AI Score" badge renders,  
Then it displays "—" and uses the muted grey style.

**AC5 — Badges are visible at 1280×800 without overlapping any chart elements**  
Given a browser window set to 1280×800,  
When the `/triangulated` page is loaded,  
Then all three confidence badges are visible in the legend area and none of them overlap the spider chart polygon, axis labels, or other legend text.

---

## Edge Cases

- **Confidence exactly at threshold boundary** (e.g. `0.80` exactly): is green (≥ 80%); `0.50` exactly is amber (≥ 50%).
- **Confidence of `1.0`**: displays as "100%".
- **Confidence of `0.0`**: displays as "0%" with red styling.
- **Badge tooltip on mobile/touch**: tooltip must be accessible via tap — not only on hover.
- **Chart resized** (browser zoom or responsive layout): badges must remain in the legend area and not drift into the chart canvas.

---

## Out of Scope
- Confidence scores for individual elements within a series — badges are per-series at the legend level only.
- Editing or overriding confidence scores.
- The comparison table (PROT-116) — a separate UI component.

## Dependencies
- PROT-115 (`GET /api/assessments/:id/triangulation`) provides the `confidences` object.
- The spider chart legend must exist as a DOM element that can host additional badge elements.

## Definition of Done
- [ ] Confidence badges rendered in spider chart legend for all three series
- [ ] Colour thresholds verified at exactly 80% and 50% boundaries in Playwright
- [ ] `null` confidence renders "—" with grey style — explicit test scenario
- [ ] Tooltip text verified with Playwright hover event
- [ ] All 5 acceptance criteria pass as named Playwright scenarios
- [ ] The generated Gherkin feature file covers each AC as a distinct scenario
