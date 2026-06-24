# SPEC: Assurance CI
Tier: PROTOTYPE · Demo: 2026-06-23 (Monday) · Domain: see DOMAIN.md

## Strategic Value
**User Value Moment**: A developer pushes a commit referencing a story ID and, without any manual effort, a PR appears with generated test cases, a runnable test script, a pass/fail execution report, a traceability register row, and a red/green gate — proving the full STLC-deliverables chain ran automatically.

**North-star**: Release approvers make deploy decisions by reading the register instead of convening manual test-evidence meetings.

**Kill signal**: Any false-green (gate green on broken code) on the 3 seed stories, or chronic false-reds (gate red on correct code) in more than 1 of 3 stories.

---

## Core Flow
1. Developer commits code with `PROT-101: ...` as the commit message and opens a PR
2. GitHub Actions `assurance` job triggers — parses the story ID, loads the matching story file from `/jira/`
3. `build_context.py` assembles a structured context payload (changed symbols, type signatures, file contents, import graph, existing tests) from the diff — `claude-code-action@v1` invokes Claude via the `/test-generation` skill, passing the story acceptance criteria + the context payload → generates a `.feature` file (Gherkin test cases) + a runnable test script (pytest-bdd for API story, Playwright for UI stories)
4. Generated tests run headlessly against the Protect AI codebase — execution report written regardless of result (`if: always()`)
5. A new row is appended to the traceability register: story → commit → generated files → result
6. `gate` job runs — any failed scenario = red status check, all passed = green
7. Approver opens the PR, reads the gate, follows the register link to see the full evidence chain

---

## Acceptance Criteria

### F1: AI test generation
**What it is:** Claude (Anthropic) generates a Gherkin feature file and a runnable test script from the story's acceptance criteria and the code diff — the core feasibility question the demo answers.

- Given PROT-101 (the API story) exists with acceptance criteria and a developer commits `PROT-101: add assessment submission endpoint`, When the CI pipeline runs, Then a feature file containing Gherkin test cases covering each acceptance criterion in PROT-101 is saved to the repo, and a runnable pytest-bdd test script is saved alongside it
- Given PROT-102 (the slider UI story) exists with acceptance criteria and a developer commits `PROT-102: add slider to self-assessment`, When the CI pipeline runs, Then a feature file with Gherkin test cases for the UI acceptance criteria is saved, and a Playwright test script is saved alongside it
- Given a developer commits `PROT-999: tweak styling` and no story PROT-999 exists, When the CI pipeline runs, Then the pipeline reports "Story PROT-999 not found — no tests generated" and no feature file or test script is written

### F2: Test execution
**What it is:** The generated test scripts run for real in CI against the Protect AI codebase, producing a concrete pass/fail execution report — proving the generated tests are runnable, not just text.

- Given a feature file and test script have been generated for PROT-101 and the API endpoint behaves correctly, When the generated tests run, Then the execution report shows all scenarios passed, including environment name, run timestamp, and commit author
- Given a deliberate defect is introduced in the Protect AI code, When the generated tests run, Then the execution report records which scenarios failed — and is still written to the repo even though tests failed

### F3: Traceability report
**What it is:** Every pipeline run produces an auditable record — a register row linking story → commit → test cases → execution result — readable by an approver without any tooling.

- Given a complete pipeline run for PROT-101 (generation + execution), When the assurance job finishes, Then the traceability register gains exactly one new row: story ID, commit SHA, author, path to feature file, path to test script, pass/fail result, timestamp — and no prior row is changed
- Given the register contains at least one completed run, When an approver opens the traceability register, Then they see a table with one row per run showing: Story | Commit | Author | Result | Date — readable without any tooling
- Given the register shows a green result for PROT-101, When an approver follows the links in that row, Then they can open the feature file listing the test cases and the execution report confirming they passed

### F4: Story-keyed pipeline trigger
**What it is:** The pipeline is triggered automatically — no developer action beyond including the story ID. The story ID is extracted from four sources in priority order: workflow dispatch input → commit message → PR title → branch name.

- Given a developer commits `PROT-101: add endpoint` and PROT-101 exists, When the commit is pushed and a PR is raised, Then the assurance pipeline starts automatically and loads PROT-101 as the source of truth for test generation
- Given no story ID is in the commit message but the PR title contains `PROT-101`, When the pipeline runs, Then PROT-101 is used as the story ID (PR title fallback)
- Given a developer commits `fix typo in README` (no story ID in commit, PR title, or branch), When the commit is pushed, Then the assurance pipeline skips without error and writes no test files or register rows

### F6: Agentic build context
**What it is:** Before Claude generates tests, `build_context.py` assembles a structured context payload from the code diff — giving Claude the information it needs to generate tests that actually run (correct imports, real symbol names, real endpoint paths). This is what separates runnable tests from plausible-looking text.

- Given a commit touches TypeScript/TSX files, When `build_context.py` runs, Then the context payload includes changed symbol names, their full type signatures, file imports, `'use client'`/`'use server'` directives, and diff excerpts — not empty fields
- Given a commit touches Python files, When `build_context.py` runs, Then the context payload includes changed function/class names extracted via AST, their callers, and diff excerpts
- Given co-located test files exist for changed files (`.test.ts`, `.spec.tsx`, `__tests__/`) or previously generated tests exist in `generated/$STORY_ID/`, When `build_context.py` runs, Then those test files are included in the context payload under `existing_tests`
- Given a file is ≤200 lines, When `build_context.py` runs, Then the full file source is included in `file_contents` so Claude can see the complete implementation

### F5: Deploy gate
**What it is:** A required status check on the PR — green unblocks merge, red blocks it. Any failed scenario = red. Simple logic; the visible signal stakeholders see.

- Given all generated test scenarios for PROT-101 passed, When the gate job completes, Then the PR shows a green "Assurance CI" status check and merge is unblocked
- Given at least one generated test scenario for PROT-102 failed, When the gate job completes, Then the PR shows a red "Assurance CI" status check and merge is blocked

---

## Seed Stories

Three stories against the existing Protect AI (`/Users/shreyas/Dev/protect`) AI-assessment feature:

### PROT-101 — API story (pytest-bdd)
**Title**: Add POST /api/assessments endpoint to persist self-assessment submissions

**Description**: Currently all assessment scores are computed client-side and lost on page refresh. Markets need an audit trail. Add a server-side API route that accepts a self-assessment submission and stores it.

**Acceptance criteria**:
- The endpoint accepts a POST request with market, element, task, selfScore (1–5), and rationale
- It returns a 200 response with an assessment ID and the submission timestamp
- It returns a 400 error if selfScore is outside the 1–5 range
- It returns a 400 error if the element value is not a recognised element name

**Test type**: pytest-bdd (HTTP API contract tests against the Next.js route handler)

---

### PROT-102 — UI story 1 (Playwright)
**Title**: Replace self-assessment numeric input with a range slider

**Description**: The current self-assessment uses a plain number input box (1–5). Replace it with a styled range slider that shows the current value live as the user drags, making the scoring more intuitive.

**Acceptance criteria**:
- A slider replaces the numeric input on the `/assessment` page
- Dragging the slider updates the displayed score value in real time
- The slider only allows values 1, 2, 3, 4, 5 (discrete steps)
- Submitting the form sends the same score value as the slider position
- The slider is visible and usable on a 1280×800 viewport

**Test type**: Playwright (UI interaction and value binding)

---

### PROT-103 — UI story 2 (Playwright)
**Title**: Show delta flag count and flagged elements on the triangulated view

**Description**: The `/triangulated` page already renders a spider chart comparing Self vs AI vs ICO scores. The `deltaFlags` data exists but is not surfaced in the UI. Add a section below the chart listing each flagged element, the score gap, and which direction it diverged.

**Acceptance criteria**:
- The `/triangulated` page shows a "Delta Flags" section below the spider chart
- Each flagged element appears as a row showing: element name, self score, AI score, and the gap (e.g. "Self: 2 · AI: 4 · Gap: +2")
- Elements with no delta flag (gap ≤ 1) do not appear in the list
- If there are no delta flags, the section shows "No significant gaps detected"
- The section is visible on a 1280×800 viewport without scrolling past the chart

**Test type**: Playwright (DOM presence and content assertions)

---

## Out of Scope
- **Real JIRA integration**: simulated via local `/jira/` story files — live API adds no feasibility signal
- **Multi-story commits**: one story ID per commit — multi-story parsing is a production concern
- **BrowserStack / cross-browser execution**: headless Playwright only — cross-browser is post-feasibility
- **Configurable rigour levels per story**: standard test suite from acceptance criteria — no per-story knobs
- **Agent-attribution traceability**: register records story→code→test→result, not which AI step did what
- **Elaborate decision UI / dashboard**: gate is a GitHub status check; register is a committed file

---

## Supporting-Domain Stubs
- **Simulated JIRA store**: static story files in `/jira/PROT-NNN.md` — served via GitHub Pages (`https://shreynp.github.io/Assurance-CI`) in CI, read from disk locally; no live JIRA API
- **Build context assembler**: `build_context.py` — extracts changed symbols, type signatures, imports, file contents, and existing tests from the diff; tree-sitter for TS/TSX/JS/JSX, Python AST for `.py`; pure data extraction, no generation logic
- **Agentic generation step**: `claude-code-action@v1` running the `/test-generation` skill — invokes Claude with context payload + story acceptance criteria; max-turns 25; `continue-on-error: true` so the pipeline always reaches append/record
- **PR body builder**: `build_pr_body.py` — renders a PR comment with gate result, test counts, RCA table (parsed from pytest `--tb=short`), and a Claude Haiku–generated plain-English RCA summary; Haiku call is best-effort (fails silently)
- **Protect AI sample app**: existing Next.js app at `/Users/shreyas/Dev/protect` — used as test substrate; deliberate defects introduced only for red-gate validation, then reverted
- **Markdown register renderer**: renders `traceability/register.json` as a committed `traceability/REGISTER.md` table — no logic, presentational only
- **GitHub Actions plumbing**: `assurance` job (generate → run → record, with `continue-on-error` on agentic + gate steps) + `gate` job (`needs: assurance`) — commodity YAML

---

## Enforcement
- Acceptance scenarios become test names and assertions verbatim — no reinterpretation
- Mid-build feature not traceable to a scenario: score against User Value Moment, then amend SPEC.md or move to Out of Scope
- Critical Assumption #1 (generation quality) must be validated against all 3 seed stories before the gate is wired — confirm green-when-correct and red-when-broken before demo
