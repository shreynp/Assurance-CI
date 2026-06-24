"""
Run generated tests via pytest and write an execution report JSON.

Inputs:
  ARG  --story-id       Story identifier, e.g. PROT-101
  ARG  --generated-dir  Root of generated output (must contain <story-id>/meta.json)
  ARG  --report-out     Directory to write <story-id>_report.json
  ENV  GITHUB_SHA       (default: "local")   — recorded in the report
  ENV  GITHUB_ACTOR     (default: $USER or "unknown") — recorded as author
  ENV  RUNNER_OS        (default: "local")   — recorded as environment string

Outputs:
  FILE <report-out>/<story-id>_report.json — schema:
       {story_id, commit_sha, author, passed, failed, environment,
        timestamp, output (truncated to 4 000 chars), exit_code}
  exit — pytest's return code (0=all passed, 1=failures/errors)

Full pytest output is printed to stdout before the report is written.
"""
import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# Matches: "3 passed, 2 failed", "3 passed", "2 failed, 1 error", "2 error"
_SUMMARY_RE = re.compile(
    r"(\d+) passed(?:,\s*(\d+) (?:failed|error))?|"
    r"(\d+) (?:failed|error)(?:,\s*(\d+) passed)?"
)


def parse_counts(output: str) -> tuple[int, int]:
    """
    Extract (passed, failed) from pytest -v output.

    Strategy: prefer the final summary line when present (more reliable than
    per-test token counting). Falls back to counting ' PASSED' / ' FAILED' /
    ' ERROR' substrings when no summary line is found (e.g. 'no tests ran').
    Errors are counted as failures in both strategies.
    """
    passed = output.count(" PASSED")
    failed = output.count(" FAILED") + output.count(" ERROR")
    for line in reversed(output.splitlines()):
        m = _SUMMARY_RE.search(line)
        if m:
            if m.group(1) is not None:
                # "N passed[, M failed/error]"
                return int(m.group(1)), int(m.group(2) or 0)
            else:
                # "N failed/error[, M passed]"
                return int(m.group(4) or 0), int(m.group(3))
    return passed, failed


def main():
    """
    Run the generated test script and write an execution report JSON.

    Implicit env-var inputs (read from environment, not CLI args):
      GITHUB_SHA    — commit SHA recorded in the report (default: 'local')
      GITHUB_ACTOR  — author name recorded in the report (default: $USER or 'unknown')
      RUNNER_OS     — environment string recorded in the report (default: 'local')

    Exits with the pytest return code so the CI step is marked failed when tests fail.
    Report output is truncated to 4 000 chars for register storage; full output is printed above.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--story-id", required=True)
    parser.add_argument("--generated-dir", required=True)
    parser.add_argument("--report-out", required=True)
    args = parser.parse_args()

    gen_dir = Path(args.generated_dir) / args.story_id
    meta_path = gen_dir / "meta.json"
    if not meta_path.exists():
        print(f"ERROR: meta.json not found at {meta_path}")
        sys.exit(1)

    meta = json.loads(meta_path.read_text())
    test_script = meta["test_script"]
    test_type = meta["test_type"]

    report_dir = Path(args.report_out)
    report_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()

    print(f"Running {test_type} tests: {test_script}")

    # Build pytest command — no external report plugins required
    cmd = [sys.executable, "-m", "pytest", test_script, "--tb=short", "-v"]

    result = subprocess.run(
        cmd, capture_output=True, text=True,
        env={**os.environ, "PYTHONPATH": str(Path(__file__).parent.parent)},
    )
    output = result.stdout + result.stderr
    print(output)

    passed, failed = parse_counts(output)

    report = {
        "story_id": args.story_id,
        "commit_sha": os.environ.get("GITHUB_SHA", "local"),
        "author": os.environ.get("GITHUB_ACTOR", os.environ.get("USER", "unknown")),
        "passed": passed,
        "failed": failed,
        "environment": os.environ.get("RUNNER_OS", "local"),
        "timestamp": now,
        "output": output[:4000],  # truncated to 4k chars for register storage; full output printed above
        "exit_code": result.returncode,
    }
    report_path = report_dir / f"{args.story_id}_report.json"
    report_path.write_text(json.dumps(report, indent=2))
    print(f"Execution report written: {report_path}")

    # Exit with test result so CI knows whether tests passed
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
