# PROT-116 — Show AI score vs self score comparison table below spider chart on /triangulated

**Type**: UI story
**Test type**: Playwright

## Description
The spider chart on /triangulated gives a visual overview but users cannot read exact values from it. Add a comparison table below the chart that shows self score, AI score, ICO benchmark, and gap for each element, making it easy to see where assessments diverge.

## Acceptance Criteria
- AC1: A table appears below the spider chart on /triangulated with columns: Element, Self Score, AI Score, ICO Benchmark, Gap
- AC2: The Gap column shows the numeric difference (selfScore − aiScore) with a "+" prefix for positive gaps
- AC3: Rows where the absolute gap exceeds 1 are highlighted with an amber background
- AC4: The table is sortable by clicking any column header
- AC5: The table is visible on a 1280×800 viewport without scrolling past the chart
