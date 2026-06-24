# Troubleshooting Guide

Common failure modes and how to diagnose them.

---

## 1. "No story ID found — skipping assurance pipeline"

**Symptom:** The "Extract story ID" step logs this message and the pipeline exits 0 without running.

**Cause:** The pipeline checks four sources in priority order: `workflow_dispatch` input → commit message → PR title → branch name. If none contain a `PROT-NNN` pattern the pipeline skips.

**Fix options:**
- Ensure your commit message matches `PROT-NNN: description` (case-sensitive, uppercase)
- Use a manual dispatch: `gh workflow run assurance.yml --ref <branch> --field story_id=PROT-101`
- Check that the story ID regex in `src/domain/commit_parser.py` matches your project's ID prefix

---

## 2. "Tests didn't collect" / "collected 0 items"

**Symptom:** The "Run generated tests" step shows `collected 0 items` or `no tests ran`.

**Cause:** Either the test files weren't generated, or the generated test has a syntax/import error that prevents collection.

**Diagnosis:**
```bash
# Check what was generated
ls generated/<story-id>/

# Try running pytest directly
pytest generated/<story-id>/ -v --collect-only

# Read the feature file and test script
cat generated/<story-id>/<story-id>.feature
cat generated/<story-id>/test_<story-id>.py
```

**Fix:** Re-trigger the pipeline with a `workflow_dispatch`. If the skill generates tests but they don't collect, check `gate_notes.md` for a failure classification — the skill writes this when tests fail to collect.

---

## 3. "Gate is red but tests look fine"

**Symptom:** The gate job exits 1 (red) but you believe the tests passed.

**Cause:** `resolve_gate.py` looks up the traceability register by `story_id + commit_sha`. A mismatch (e.g. an amended commit changing the SHA) will produce "no record found → red".

**Diagnosis:**
```bash
# Inspect gate.json
cat /tmp/gate.json   # in the CI run artifacts

# Check the register for this story
python3 -c "
import json
r = json.load(open('traceability/register.json'))
matches = [x for x in r if x['story_id'] == 'PROT-101']
print(json.dumps(matches[-3:], indent=2))
"
```

**Fix:** Ensure `--commit-sha` in the `resolve_gate.py` call matches the full SHA that was used when `append_record.py` ran. Re-run with `workflow_dispatch` if needed.

---

## 4. "Dev server didn't start" / wait-on timeout

**Symptom:** The "Wait for dev server" step times out with `Timed out waiting for: http://localhost:3000`.

**Cause:** The dev server startup took longer than 60 seconds, or failed to start (e.g. missing env var, port conflict).

**Diagnosis:**
```bash
# Check the dev server log in the CI run
cat /tmp/dev.log
```

**Fix options:**
- Increase the `wait-on` timeout in `assurance.yml` (change `60000` to `120000`)
- Check that `npm run dev` succeeds locally in the same environment
- Ensure `NODE_ENV=development` is set (some apps require it to start)

---

## 5. Agentic step exits at max turns

**Symptom:** The "Generate and validate tests" step log shows `Reached max turns (25)` and the step completes via `continue-on-error: true`. Generated files may be partial or absent.

**Cause:** `claude-code-action@v1` is capped at `--max-turns 25`. Hitting the cap happens when a story has many acceptance criteria, the changed codebase has many files, or context loading takes more turns than expected.

**Impact:** Tests may be partially generated or missing. `meta.json` may not have been written, causing `append_record.py` to fail with `FileNotFoundError`.

**Diagnosis:**
```bash
# Check what was generated before the cap
ls generated/<story-id>/

# Check for meta.json (required by append_record.py)
cat generated/<story-id>/meta.json

# Check gate_notes.md for any classification written before cap
cat generated/<story-id>/gate_notes.md
```

**Fix:** Re-run via `workflow_dispatch` — Claude will often complete successfully on a second attempt. If it consistently hits the cap, the story may have too many acceptance criteria for one run. Consider splitting the story.

---

## 6. "Diff truncated" / large changeset warnings (legacy)

> **Note:** The old 8 000-character raw diff cap no longer applies. `build_context.py` replaced raw diff piping with structured AST extraction — only changed symbols and their targeted diff lines are included, not the entire diff. Each file's context is bounded by the `≤200-line` `file_contents` limit. If you see context warnings, see section 5 (turn cap) rather than a diff size limit.

---

## Inspecting Pipeline Artifacts Locally

```bash
# After a CI run, pull traceability artifacts
git pull

# Read the last register entry
python3 -c "import json; r=json.load(open('traceability/register.json')); print(json.dumps(r[-1], indent=2))"

# Read the generated tests for a story
ls generated/PROT-101/
cat generated/PROT-101/gate_notes.md  # present only when tests fail
```
