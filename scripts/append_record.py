"""Append a traceability record to the register. Called after test run."""
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
      <generated-dir>/<story-id>/meta.json   — written by generate_tests.py
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
