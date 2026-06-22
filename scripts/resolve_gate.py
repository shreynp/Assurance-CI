"""Read register, find the latest run for story+commit, output gate.json."""
import argparse
import json
import sys
from pathlib import Path


def main():
    """
    Read the register and resolve the gate status for a specific story+commit.

    Exits 0 if the latest gate for story+commit is green, exits 1 if red or
    if no matching record exists.

    When multiple records share the same story_id + commit_sha, the last
    (most recently appended) record is used.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--register", required=True)
    parser.add_argument("--story-id", required=True)
    parser.add_argument("--commit-sha", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    register_path = Path(args.register)
    if not register_path.exists():
        gate = {"status": "red", "reason": "Register not found — no test evidence"}
    else:
        try:
            records = json.loads(register_path.read_text())
        except json.JSONDecodeError as exc:
            print(f"ERROR: register file contains invalid JSON — {exc}")
            sys.exit(1)
        matches = [
            r for r in records
            if r.get("story_id") == args.story_id and r.get("commit_sha") == args.commit_sha
        ]
        if not matches:
            gate = {"status": "red", "reason": f"No record found for {args.story_id} @ {args.commit_sha[:7]}"}
        else:
            latest = matches[-1]
            gate = latest["gate_result"]

    Path(args.output).write_text(json.dumps(gate, indent=2))
    print(f"Gate: {gate['status'].upper()} — {gate['reason']}")
    sys.exit(0 if gate["status"] == "green" else 1)


if __name__ == "__main__":
    main()
