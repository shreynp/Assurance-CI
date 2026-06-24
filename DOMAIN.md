# DOMAIN: Assurance CI

## Business Thesis
- **Objective**: Feasibility probe — answer two questions Pfizer needs before committing to the Assurance Line: (1) Can AI generate meaningful, executable test cases and scripts from a story + diff today? (2) Can the full chain — story → commit → generated test cases → execution → traceability report → gate — be assembled end-to-end in CI? The demo either proves both are possible, or surfaces exactly where the chain breaks. That answer is the deliverable.
- **Buyer / User**: Buyer = Pfizer assurance-program sponsor (needs compliance/audit evidence) · Daily user = developer committing against a JIRA story · Secondary user = release approver reading the gate + register · **Divergence**: buyer wants gate strictness and rigor (any failed scenario = red); developer wants speed and no false-red blocks — a gate strict enough for the buyer is exactly what frustrates the developer if generated tests are noisy.
- **Why now**: AI (Claude / Anthropic) can now reliably generate Gherkin feature files and runnable tests (pytest-bdd / Playwright) from a story + code diff — work that previously required manual SDET authoring and was therefore never done per-commit. Pfizer is simultaneously defining the Assurance Line across the SDLC and needs to prove the STLC-deliverables stop concretely.
- **Moat**: Regulatory/compliance moat + switching cost. The wired-in, auditable story→code→test→execution→gate chain becomes the system of record for deploy evidence. In pharma, once the register is the trusted source for audits and the gate is the required status check, ripping it out requires re-proving compliance continuity — not a technical swap.
- **Kill signal**: Leading indicator at the prototype itself — any false-green (gate green on broken code) on the 3 seed stories is an immediate kill; chronic false-reds (gate red on correct code in >1 of 3 stories) is a kill. At 6 months in real use — gate results overridden on >20% of red gates across 3 consecutive weeks (developers route around it as noise), OR story IDs absent from >30% of commits (convention not adopted), OR approvers revert to manual verification meetings (register not trusted). The first false-green is the fastest path to death: it destroys approver trust permanently and is exactly the failure the strict "any failed scenario = red" rule cannot protect against.
- **North-star behavior**: At 12 months — developers habitually commit with story IDs and trust the gate; release sign-offs cite the register instead of convening manual test-evidence meetings. Manual test-evidence reconstruction disappears from the release process.

## Critical Assumptions
| # | Assumption | Status | How to test |
|---|-----------|--------|-------------|
| 1 | **PROTOTYPE MUST TEST THIS FIRST** — Claude (Anthropic) generates tests from story + diff that are correct and meaningful enough to gate deploys on: green when code is correct, red when genuinely broken, and not noisy (no false reds on correct code, no false greens on broken code). This sits directly under the Core Domain — the entire chain's evidentiary value collapses if the gate is untrustworthy. | **unknown — existential** | Run against the 3 seed stories; for each, inspect the generated feature file + test script, then deliberately break the code and confirm the gate flips red; confirm it stays green when code is correct. A single false-green or chronic false-red kills the thesis. |
| 2 | The commit-convention (story ID in commit message, e.g. `PROT-101`) is reliably followed and parseable — the entire chain keys off it | assumed | Parser handles realistic commit message formats; measure story-ID presence rate across sample commits |
| 3 | A red/green required status check + the register is a sufficient and trusted deploy gate — approvers will rely on it rather than manual sign-off | assumed | In the demo, an approver makes a deploy decision using only the register and the gate result |

## Bounded Context
**In scope**: Story parsing → AI test generation → test execution → execution report → register append → gate resolution, for commits against the Protect AI codebase, covering three seed stories (one API, two UI).
**Deliberately excluded**: Real JIRA integration, agent-attribution traceability ("which agent did what"), configurable rigor levels per story, BrowserStack execution, elaborate decision UI, multi-repo or multi-project support.

## Ubiquitous Language
| Term | Meaning | Notes |
|------|---------|-------|
| Story | Simulated JIRA ticket file with ID, title, description, and acceptance criteria | IDs like `PROT-101`; no real JIRA integration |
| Acceptance criteria | The conditions in the story that generated tests must verify | Source of truth for test correctness |
| Commit convention | Commit message must contain the story ID; the pipeline keys off this | Format: `PROT-101: ...` |
| Feature file | AI-generated Gherkin `.feature` file capturing test cases for a story | Output of the generation step |
| Test script | AI-generated runnable test — pytest-bdd for API stories, Playwright for UI stories | Executed in CI headlessly |
| Execution report | Pass/fail result + environment + timestamp + commit author for one pipeline run | Written before gate resolves |
| Register | Append-only traceability record in `traceability/register.json` with a rendered markdown view | The compliance system of record |
| Gate | Red/green required status check on the PR; any failed scenario = red | The deploy signal |
| Protect AI | Existing Next.js app — serves as both the sample codebase and the test repo | AI-assessment feature is the target |
| Assurance Line | Pfizer's SDLC-wide assurance track; this prototype proves its "STLC deliverables" stop | Buyer context |

## Entities & Value Objects
| Name | Type | Key Fields | Lifecycle |
|------|------|-----------|-----------|
| Story | Entity | `id` (PROT-NNN), `title`, `description`, `acceptance_criteria[]` | Exists as a static file; loaded when commit references its ID |
| Commit | Value Object | `sha`, `author`, `message`, `pr_title`, `branch_name`, `story_id`, `diff` | Immutable; captured at pipeline trigger; story ID resolved from message → pr_title → branch_name in that priority order |
| BuildContext | Value Object | `story_id`, `commit_sha`, `changed_symbols`, `symbol_signatures`, `file_contents`, `file_imports`, `file_directives`, `existing_tests`, `diff_excerpts` | Assembled by `build_context.py` from the diff before the agentic step; passed to Claude as structured input; immutable after assembly |
| FeatureFile | Entity | `story_id`, `commit_sha`, `gherkin_content`, `generated_at` | Created by AI generation step; immutable after write |
| TestScript | Entity | `story_id`, `commit_sha`, `type` (pytest-bdd / playwright), `content`, `generated_at` | Created by AI generation step; immutable after write |
| ExecutionReport | Entity | `story_id`, `commit_sha`, `passed`, `failed`, `environment`, `timestamp`, `author` | Created after test run; immutable; written even on failure (`if: always()`) |
| TraceabilityRecord | Entity | `story_id`, `commit_sha`, `author`, `feature_file_path`, `test_script_path`, `execution_report`, `gate_result`, `appended_at` | Appended to register; never mutated after append |
| GateResult | Value Object | `status` (red / green), `reason` | Derived from execution report; any failed scenario → red |
| PRBody | Value Object | `story_id`, `gate_result`, `passed`, `failed`, `rca_table`, `rca_summary` | Rendered by `build_pr_body.py`; posted as PR comment; RCA summary generated by Claude Haiku (best-effort) |

## Domain Events
- **CommitParsed** — story ID extracted from commit message, PR title, or branch name (in that priority order); the qualifying change is recognized
- **StoryResolved** — parsed story ID matched to a story file and its acceptance criteria loaded; the chain now has its source of truth (or fails loudly if no story matches — Assumption #2 lives here)
- **BuildContextAssembled** — `build_context.py` has extracted changed symbols, type signatures, file contents, imports, and existing tests from the diff; the context payload is ready for the agentic step
- **FeatureFileGenerated** — Gherkin feature file written from story + context payload; marks generation step complete
- **TestScriptGenerated** — runnable test written; ready for execution
- **TestsExecuted** — execution report recorded (pass or fail); pipeline continues regardless of result
- **TraceabilityRecordAppended** — one row committed to the register; the durable audit artifact exists
- **GateResolved** — red or green status check set on the PR; the deploy decision is available

## Core Domain
**Three STLC deliverables — all three must be demonstrated to prove the thesis:**

1. **Test cases + scripts (generation)** — Claude (Anthropic) produces a Gherkin `.feature` file and a runnable test (pytest-bdd / Playwright) from story + diff that genuinely verifies the acceptance criteria. This is the existential unknown: the demo exists to find out if this works at all.
2. **Execution** — the generated scripts actually run in CI and produce a real pass/fail result against the Protect AI codebase. Headless Playwright for UI stories; pytest-bdd for the API story.
3. **Traceability report** — a human-readable artifact showing the full story → commit → test cases → execution result chain, in a form an approver can read and sign off on. This is what makes the gate meaningful — without it, the red/green is just a number with no evidence behind it.

The gate (red/green required status check) is derived from the execution result: any failed scenario = red. It is simple logic, not craft.

- Gets: working generation prompt, real test execution, readable traceability output
- The hard and unknown part is #1 — tune it against all three seed stories until green-when-correct / red-when-broken

## Supporting / Generic
- **Simulated JIRA store**: static `/jira/PROT-NNN.md` files — served via GitHub Pages in CI, read from disk locally; no real API; no craft investment
- **Build context assembler**: `build_context.py` — tree-sitter (TS/TSX/JS/JSX) + Python AST; extracts changed symbols, signatures, imports, file contents, existing tests; pure data extraction; the *input* to the core domain craft
- **Agentic generation step**: `claude-code-action@v1` running the `/test-generation` skill — the HTTP call and action wiring are commodity; the skill prompt and context payload design are core domain craft
- **PR body builder**: `build_pr_body.py` — commodity rendering; Claude Haiku RCA call is best-effort; no craft investment
- **GitHub Actions plumbing**: workflow YAML for `assurance` + `gate` jobs — commodity CI configuration
- **Markdown register renderer**: renders `register.json` to a readable markdown table — no logic, presentational only
- **Protect AI sample app**: existing Next.js app used as test substrate — not built here

---
## Enforcement (binding for the full build)
- All code, UI labels, fixtures, and test names use ubiquitous-language terms verbatim
- Core domain logic: pure functions in `src/domain/`, zero UI imports, unit-testable in isolation
- Supporting domains: cheapest thing that demos well — no craft investment
- Mid-build concept not in glossary: stop, add it or reject it
- Mid-build feature not traceable to Business Thesis or Critical Assumption: Out of Scope
- Critical Assumption proven false: surface it — do not paper over it
