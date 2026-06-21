"""Render traceability/register.json → traceability/REGISTER.md."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.domain.register import render_markdown


def main():
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
