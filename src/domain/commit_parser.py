"""Pure domain logic: extract story ID from a commit message."""
from __future__ import annotations
import re

# Matches PROT-NNN story IDs only (e.g. "PROT-101", "PROT-202").
# Anchored to PROT to avoid false matches on tokens like UTF-8, HTTP-2, SHA-256.
# Examples that match: "PROT-101: fix", "fix PROT-202 slider"
# Examples that don't match: "prot-101" (lowercase), "PROT-" (no number), "UTF-8"
STORY_ID_PATTERN = re.compile(r"\b(PROT-\d+)\b")


def extract_story_id(commit_message: str) -> str | None:
    """Return the first story ID found in the commit message, or None."""
    match = STORY_ID_PATTERN.search(commit_message)
    return match.group(1) if match else None


def has_story_id(commit_message: str) -> bool:
    """Return True if the message contains at least one story ID of the form PROJECT-NNN."""
    return extract_story_id(commit_message) is not None
