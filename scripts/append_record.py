"""Append a traceability record to the register after a test run.

Inputs:
  ARG  --story-id       Story identifier, e.g. PROT-101
  ARG  --commit-sha     Full commit SHA
  ARG  --author         Commit author (GITHUB_ACTOR or git user name)
  ARG  --generated-dir  Root of generated output, e.g. generated/
                        Must contain <story-id>/meta.json (written by the test-generation skill)
  ARG  --report-dir     Directory containing <story-id>_report.json (written by run_tests.py)
  ARG  --register       Path to traceability/register.json (created if absent)

Outputs:
  FILE traceability/register.json — record appended with schema:
       {story_id, commit_sha, author, feature_file_path, test_script_path,
        execution_report: {passed, failed, environment, timestamp, output},
        gate_result: {status, reason}, appended_at}
  exit 0 — record appended successfully
  exit 1 — meta.json or report JSON not found
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.domain.models import ExecutionReport, GateResult, TraceabilityRecord
from src.domain.register import append_record


def main():
    """
    Append a traceability record to the register after a test run.

    Expected directory layout:
      <generated-dir>/<story-id>/meta.json   — written by the test-generation skill
      <report-dir>/<story-id>_report.json    — written by run_tests.py
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--story-id", required=True)
    parser.add_argument("--commit-sha", required=True)
    parser.add_argument("--author", required=True)
    parser.add_argument("--generated-dir", required=True)
    parser.add_argument("--report-dir", required=True)
    parser.add_argument("--register", required=True)
    args = parser.parse_args()

    gen_dir = Path(args.generated_dir) / args.story_id
    meta = json.loads((gen_dir / "meta.json").read_text())

    report_path = Path(args.report_dir) / f"{args.story_id}_report.json"
    if not report_path.exists():
        print(f"ERROR: execution report not found at {report_path}")
        sys.exit(1)

    raw = json.loads(report_path.read_text())
    report = ExecutionReport(
        story_id=args.story_id,
        commit_sha=args.commit_sha,
        author=args.author,
        passed=raw["passed"],
        failed=raw["failed"],
        environment=raw["environment"],
        timestamp=raw["timestamp"],
        output=raw.get("output", ""),
    )
    gate = GateResult.from_report(report)
    now = datetime.now(timezone.utc).isoformat()

    record = TraceabilityRecord(
        story_id=args.story_id,
        commit_sha=args.commit_sha,
        author=args.author,
        feature_file_path=meta["feature_file"],
        test_script_path=meta["test_script"],
        execution_report=report,
        gate_result=gate,
        appended_at=now,
    )

    register_path = Path(args.register)
    register_path.parent.mkdir(parents=True, exist_ok=True)
    append_record(record, register_path)
    print(f"Record appended to {register_path} — gate: {gate.status.upper()}")


if __name__ == "__main__":
    main()
