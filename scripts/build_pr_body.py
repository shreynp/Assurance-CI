"""
Build a PR body markdown file from gate.json and the execution report.

Inputs:
  ARG  --story-id   Story identifier, e.g. PROT-101
  ARG  --gate       Path to gate.json (written by resolve_gate.py)
  ARG  --report-dir Directory containing <story-id>_report.json (optional — defaults to 0/0 counts)
  ARG  --out        Path to write the output markdown
  ENV  JIRA_DATA_URL        (optional) Base URL used to render a clickable ticket link
  ENV  ANTHROPIC_API_KEY    (optional) If present, calls Claude Haiku to generate a 2–3 sentence
                            plain-English RCA summary appended after the failure table.
                            Falls back silently (no summary) if absent or if the call fails.

Outputs:
  FILE <out>  Markdown PR body: gate badge, test result counts, RCA table (on failure),
              AI-generated RCA paragraph (on failure, requires ANTHROPIC_API_KEY),
              and a collapsible pytest output block.
  exit 0 — always (output is written regardless of gate status)

Usage:
  python scripts/build_pr_body.py \\
    --story-id PROT-101 \\
    --gate /tmp/gate.json \\
    --report-dir traceability/reports/ \\
    --out /tmp/pr_body.md
"""
import argparse
import json
import os
import re
from pathlib import Path


def parse_failures(output: str) -> list[dict]:
    """Extract per-test failure summaries from pytest --tb=short output.

    Returns a list of dicts with keys:
      - test:   short test identifier (file::test_name)
      - reason: one-line exception message from the summary section
      - detail: first assertion/error lines from the failure block (may be empty)
    """
    failures = []

    # 1. Parse "short test summary info" section for the one-liner per failure.
    # Greedy first group so parameterized IDs like test_fn[a - b] aren't truncated.
    for m in re.finditer(r"^FAILED (.+) - (.+?)$", output, re.MULTILINE):
        test_path = m.group(1).strip()
        reason = m.group(2).strip()
        # Drop generated/STORY_ID/ prefix so the table stays readable.
        short_name = re.sub(r"^generated/[^/]+/", "", test_path)
        failures.append({"test": short_name, "reason": reason, "detail": ""})

    if not failures:
        return failures

    # 2. Augment with the first `E ` assertion lines from each failure block.
    #    Blocks are delimited by lines of underscores.
    block_header_re = re.compile(r"^_{5,} (.+?) _{5,}$", re.MULTILINE)
    blocks: list[tuple[str, str]] = []
    headers = list(block_header_re.finditer(output))
    for i, h in enumerate(headers):
        end = headers[i + 1].start() if i + 1 < len(headers) else len(output)
        blocks.append((h.group(1).strip(), output[h.end():end]))

    # Match blocks back to failures by full test path, falling back to function name.
    # Using only the function name can match the wrong block when multiple test files
    # define a function with the same name (common in generated suites).
    for failure in failures:
        test_id = failure["test"]            # e.g. test_PROT-114.py::test_ac1_...
        test_fn = test_id.split("::")[-1]    # fallback: just the function name
        for block_name, block_body in blocks:
            if test_id in block_name or test_fn == block_name.strip():
                error_lines = [
                    line[1:].strip()  # strip leading "E"
                    for line in block_body.splitlines()
                    if line.startswith("E ")
                ]
                if error_lines:
                    # Keep at most 3 lines to stay "brief".
                    failure["detail"] = " · ".join(error_lines[:3])
                break

    return failures


def generate_worded_rca(failures: list[dict]) -> str:
    """Call Claude Haiku to produce a brief natural-language RCA paragraph.

    Returns an empty string if the API key is absent or the call fails — the
    table-only RCA is always rendered regardless.
    """
    try:
        import anthropic

        failure_text = "\n".join(
            f"- {f['test']}: {f['reason']}"
            + (f" — {f['detail']}" if f["detail"] else "")
            for f in failures
        )
        client = anthropic.Anthropic()
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            messages=[
                {
                    "role": "user",
                    "content": (
                        "You are a QA engineer writing a root cause analysis for a CI report. "
                        "Summarize the following test failures in 2–3 concise sentences. "
                        "Focus on the likely root cause, not just restating what failed. "
                        "Be specific and actionable. Do not use bullet points.\n\n"
                        f"Failed tests:\n{failure_text}"
                    ),
                }
            ],
        )
        return msg.content[0].text.strip()
    except Exception as e:
        import sys
        print(f"[build_pr_body] RCA summary skipped: {e}", file=sys.stderr)
        return ""


def main():
    """
    Build a markdown PR body from gate.json and the execution report.

    When the report JSON is absent the counts silently default to 0/0 (no error raised).
    The output file is always overwritten. JIRA_DATA_URL being absent produces a plain
    story-ID reference instead of a hyperlink.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--story-id", required=True)
    parser.add_argument("--gate", required=True)
    parser.add_argument("--report-dir", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    gate = json.loads(Path(args.gate).read_text())
    report_path = Path(args.report_dir) / f"{args.story_id}_report.json"
    report = json.loads(report_path.read_text()) if report_path.exists() else {}

    status = gate.get("status", "red")
    reason = gate.get("reason", "")
    badge = "✅ GREEN" if status == "green" else "❌ RED"

    passed = report.get("passed", 0)
    failed = report.get("failed", 0)
    output = report.get("output", "")
    commit_sha = (report.get("commit_sha", "") or "")[:7]
    timestamp = (report.get("timestamp", "") or "")[:19].replace("T", " ")

    jira_base = os.environ.get("JIRA_DATA_URL", "").rstrip("/")
    ticket_ref = (
        f"[{args.story_id}]({jira_base}/{args.story_id}.md)"
        if jira_base
        else args.story_id
    )

    lines = [
        f"## Assurance CI Report — {args.story_id}",
        "",
        f"**Ticket**: {ticket_ref}  ",
        f"**Commit**: `{commit_sha}`  **Run**: {timestamp} UTC",
        "",
        "### Gate",
        "",
        f"**{badge}** — {reason}",
        "",
        "### Test Results",
        "",
        "| | Count |",
        "|:---|---:|",
        f"| ✅ Passed | **{passed}** |",
        f"| ❌ Failed | **{failed}** |",
        "",
    ]

    failures = parse_failures(output) if failed > 0 else []
    if failures:
        lines += [
            "### Root Cause Analysis",
            "",
            "| Test | Failure | Detail |",
            "|:-----|:--------|:-------|",
        ]
        for f in failures:
            test = f["test"].replace("|", "\\|")
            reason = f["reason"].replace("|", "\\|")
            detail = (f["detail"] or "—").replace("|", "\\|")
            lines.append(f"| `{test}` | `{reason}` | {detail} |")
        lines.append("")

        worded = generate_worded_rca(failures)
        if worded:
            lines += [
                "> **Summary**: " + worded.replace("\n", " "),
                "",
            ]

    if output.strip():
        lines += [
            "<details>",
            "<summary>Test output</summary>",
            "",
            "```",
            output.strip(),
            "```",
            "",
            "</details>",
            "",
        ]

    lines += [
        "---",
        "_Generated by Assurance CI · "
        "Traceability record committed to `traceability/register.json`_",
    ]

    Path(args.out).write_text("\n".join(lines), encoding="utf-8")
    print(f"PR body written to {args.out}")


if __name__ == "__main__":
    main()
