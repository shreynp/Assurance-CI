"""I/O wrapper: read a story file and delegate parsing to the pure domain layer."""
from __future__ import annotations
from pathlib import Path

from src.domain.story_parser import parse_story_text
from src.domain.models import Story


def load_story(story_id: str, jira_dir: Path) -> Story:
    """
    Read <jira_dir>/<story_id>.md and parse it into a Story.

    Raises FileNotFoundError if the file does not exist.
    Raises ValueError if the file contains no acceptance criteria.
    """
    story_file = jira_dir / f"{story_id}.md"
    if not story_file.exists():
        raise FileNotFoundError(f"Story {story_id} not found in {jira_dir}")
    text = story_file.read_text(encoding="utf-8")
    return parse_story_text(text, story_id)
