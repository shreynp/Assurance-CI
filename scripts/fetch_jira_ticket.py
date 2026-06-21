"""
Fetch a ticket markdown file from a remote data source and write it to jira/<STORY_ID>.md.
The remote source must serve the file in the format expected by story_loader.py
(## Acceptance Criteria with - AC1: … bullets).

Required env var:
  JIRA_DATA_URL  Base URL without trailing slash.
                 e.g. https://raw.githubusercontent.com/org/Assurance-CI/main/jira

Usage:
  python scripts/fetch_jira_ticket.py --story-id PROT-101 --jira-dir jira/
"""
import argparse
import os
import urllib.request
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--story-id", required=True)
    parser.add_argument("--jira-dir", default="jira")
    args = parser.parse_args()

    base_url = os.environ["JIRA_DATA_URL"].rstrip("/")
    url = f"{base_url}/{args.story_id}.md"

    print(f"Fetching {args.story_id} from {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "assurance-ci/1.0"})
    with urllib.request.urlopen(req) as resp:
        content = resp.read().decode("utf-8")

    jira_dir = Path(args.jira_dir)
    jira_dir.mkdir(parents=True, exist_ok=True)
    out_path = jira_dir / f"{args.story_id}.md"
    out_path.write_text(content, encoding="utf-8")
    print(f"Written: {out_path}")


if __name__ == "__main__":
    main()
