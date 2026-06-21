# TASK: Assurance CI — story-to-gate traceability pipeline

## One-Line Summary
A CI pipeline that, when a developer commits code referencing a JIRA story ID, uses AI to generate and run tests from the story + the code change, then records the result in a readable traceability register and returns a red/green deploy gate.

## Problem Being Solved
Today there is no automated, auditable link between *what was asked* (a story), *what changed* (a commit), *how it was verified* (test cases + execution), and *whether it's safe to ship* (a gate). Verification is manual and the chain is reconstructed after the fact. This proves the "STLC deliverables" stop of Pfizer's Assurance Line: test cases, scripts, and traceability generated automatically, with a human sign-off gate where it matters.

## Primary User
A developer working a JIRA story against the Protect AI (Next.js) codebase — they edit code and commit with the story ID; everything downstream is automated. A secondary reader is the release approver who looks at the red/green gate and the register to decide deploy / don't.

## Core Functionality
A GitHub Actions workflow triggered on push/PR that:
1. Parses the commit message for JIRA story ID(s) (e.g. `PROT-101`).
2. Loads the matching story file (simulated JIRA — local files, no real integration).
3. Calls Claude (Anthropic) with the story + the changed code to generate a Gherkin `.feature` file (test cases), then the runnable test — **pytest-bdd** for the API story, **Playwright** for the UI stories.
4. Runs the tests (headless Playwright by default for reliability).
5. Writes an execution report: pass/fail, environment, timestamp, commit author.
6. Appends a traceability record to a committed register.
7. Resolves to a **red/green required status check** — the deploy gate.

**Traceability** here means exactly: story → code change → test cases → execution report, in a register you can read back. *Not* "which agent did what" — explicitly out of scope.

## Key Screens / Flows

| Screen / Flow | What the user does | What the system shows |
|---------------|-------------------|----------------------|
| Commit (primary) | Edits Protect AI code, commits with `PROT-101: ...`, raises a PR | CI kicks off, parses the story ID |
| Test generation | (automated) | Claude emits a `.feature` file + a runnable test from story + diff |
| Test execution | (automated) | pytest-bdd / Playwright run, pass/fail report |
| Register | Reads back the register | Story ID, commit SHA, author, generated files, results, timestamp |
| Gate | Reads the status check | Red (block) or green (deploy) on the PR |

## Entities & Vocabulary

| Term | What it means in this context |
|------|-------------------------------|
| Story (JIRA) | A simulated ticket file with ID, title, description, acceptance criteria (IDs like `PROT-101`) |
| Acceptance criteria | The conditions in the story the generated tests must verify |
| Commit convention | Commit message must contain the story ID; the pipeline keys off this |
| Feature file | The generated Gherkin `.feature` capturing test cases |
| Test script | The runnable test — pytest-bdd (API) or Playwright (UI) |
| Execution report | pass/fail + environment + timestamp + commit author for one run |
| Register | The committed, append-only traceability record (`traceability/register.json` or markdown table) |
| Gate | The red/green required status check that says deploy or don't |
| Protect AI | The existing Next.js app used as both the sample codebase and the test repo |
| Assurance Line | Pfizer's SDLC-wide assurance track; this proves its "STLC deliverables" stop |

## Constraints & Context
- **Codebase**: existing Protect AI (Next.js) app, pushed to a new repo under the newpage GitHub ID — serves as both sample code and test repo.
- **No real JIRA**: simulate with a `/jira/` folder of story files (or one `jira.json`). Three stories tied to the existing AI-assessment feature: one API story, two UI stories.
- **Test stacks**: pytest-bdd (API), Playwright (UI).
- **Execution**: headless Playwright is the default; BrowserStack (free account) is a stretch goal only if time allows.
- **CI**: GitHub Actions on push/PR; two jobs — `assurance` (generate → run → record) then `gate` (`needs: assurance`). Report-writing and register-append steps use `if: always()` so a failing run still commits its evidence before the gate goes red. Required status check on `gate` is sufficient for the deploy signal.
- **Timeline**: build target is Monday; per-section budgets given (repo 30m, JIRA sim 30m, workflow = most of the day, register + gate 45m).
- **Scope discipline**: "do not go beyond what I just spoke about." No agent-attribution traceability, no elaborate decision UI — the gate is just a status check. The diagram's "to your rigour" wording is unconfirmed (Srish to confirm with AB).

## What Success Looks Like
A developer commits a code change to the Protect AI repo with a story ID in the message and opens a PR. CI automatically generates a `.feature` file and a runnable test from that story plus the diff, runs them, writes an execution report, appends a row to the traceability register, and turns the PR's status check red or green — and a reviewer can read the register back to see story → commit → tests → result for that change.

## Open Questions for /domain-model
- Confirm the meaning of "to your rigour" (Srish to confirm with AB) — does it imply configurable rigour levels per story, or is it just flavor text? Default assumption: flavor; generate a sensible standard test suite.
- Register format: `register.json` vs. a markdown table — which is more useful for "read back"? (Leaning JSON for machine-append + a rendered markdown view.)
- How are the three seed stories chosen against the existing AI-assessment feature — what API endpoint and which two UI flows already exist to test against?
- Gate semantics on partial failure: does any failed scenario = red, or is there a threshold? (Default: any failure = red.)

---
*Source: Text brief from Srish (the "flow to prove" + Monday build plan) plus three Pfizer strategy slides — `image.png` (The Assurance Line across the SDLC), `image (4).png` (Metro platform overview), and `image (6).png` (the "6 · STLC deliverables" card this task proves).*
