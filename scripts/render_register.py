"""Render the traceability register JSON as a human-readable Markdown table.

Inputs:
  ARG  --register  Path to traceability/register.json

Outputs:
  FILE <register-dir>/REGISTER.md — Markdown table with columns:
       Story | Commit | Author | Result | Date
  exit 0 — always
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.domain.register import render_markdown


def main():
    """
    Render register.json → REGISTER.md, always written as a sibling of the register file.

    Raises json.JSONDecodeError uncaught when the register file contains malformed JSON.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--register", required=True)
    args = parser.parse_args()

    register_path = Path(args.register)
    md = render_markdown(register_path)
    out_path = register_path.parent / "REGISTER.md"
    out_path.write_text(f"# Traceability Register\n\n{md}")
    print(f"REGISTER.md written ({len(md)} chars)")


if __name__ == "__main__":
    main()
