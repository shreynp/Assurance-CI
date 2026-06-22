"""
Generate a Gherkin feature file and a runnable test script from a story + diff.
Called by the assurance CI workflow.
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import anthropic

from src.domain.generator import build_feature_prompt, build_test_script_prompt, strip_fences
from src.io.story_loader import load_story

JIRA_DIR = Path(__file__).parent.parent / "jira"


def main():
    """
    Generate a Gherkin feature file and a runnable test script for a story.

    Steps: (1) load story from jira/, (2) call Claude twice (feature then
    test script), (3) write outputs + meta.json to <out>/<story-id>/.

    Required env var:
      ANTHROPIC_API_KEY  — Claude API key (no default; aborts if unset)

    Implementation notes:
      - Diff is capped at 8 000 chars before being sent to the prompt.
      - Model is hardcoded to claude-opus-4-8; change the constant in this file to switch.
      - If Claude returns a response with no text block (e.g. only tool-use blocks),
        the script prints "ERROR: Claude returned no text block" and exits 1.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--story-id", required=True)
    parser.add_argument("--diff", required=True, help="Path to diff file")
    parser.add_argument("--out", required=True, help="Output directory root")
    args = parser.parse_args()

    story = load_story(args.story_id, JIRA_DIR)
    # cap diff at 8k chars to stay within prompt token budget; larger diffs are truncated silently
    diff_text = Path(args.diff).read_text()[:8000]

    out_dir = Path(args.out) / args.story_id
    out_dir.mkdir(parents=True, exist_ok=True)

    client = anthropic.Anthropic()
    now = datetime.now(timezone.utc).isoformat()

    # 1. Generate feature file
    print(f"Generating feature file for {args.story_id}...")
    feature_resp = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=2048,
        messages=[{
            "role": "user",
            "content": build_feature_prompt(story, diff_text),
        }],
    )
    _feature_block = next((block.text for block in feature_resp.content if block.type == "text"), None)
    if _feature_block is None:
        print("ERROR: Claude returned no text block for feature generation — aborting")
        sys.exit(1)
    feature_text = strip_fences(_feature_block.strip())
    feature_path = out_dir / f"{args.story_id}.feature"
    feature_path.write_text(feature_text)
    print(f"  Written: {feature_path}")

    # 2. Generate test script
    print(f"Generating {story.test_type} test script...")
    test_filename = (
        f"test_{args.story_id.lower().replace('-','_')}.py"
        if story.test_type == "pytest-bdd"
        else f"test_{args.story_id.lower().replace('-','_')}_ui.py"
    )

    test_resp = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=4096,
        messages=[{"role": "user", "content": build_test_script_prompt(story, feature_text, feature_path.name)}],
    )
    _test_block = next((block.text for block in test_resp.content if block.type == "text"), None)
    if _test_block is None:
        print("ERROR: Claude returned no text block for test script generation — aborting")
        sys.exit(1)
    test_text = strip_fences(_test_block.strip())
    test_path = out_dir / test_filename
    test_path.write_text(test_text)
    print(f"  Written: {test_path}")

    # Write metadata for downstream scripts
    meta = {
        "story_id": args.story_id,
        "test_type": story.test_type,
        "feature_file": str(feature_path),
        "test_script": str(test_path),
        "generated_at": now,
    }
    (out_dir / "meta.json").write_text(json.dumps(meta, indent=2))
    print(f"  Meta: {out_dir / 'meta.json'}")


if __name__ == "__main__":
    main()
