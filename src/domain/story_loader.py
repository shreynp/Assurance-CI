"""Pure story parsing — no I/O. File loading lives in src/io/story_loader.py."""
from __future__ import annotations
import re
from .models import Story


# Normalises the case-insensitive regex capture to canonical Literal values
_TEST_TYPE_MAP = {
    "pytest-bdd": "pytest-bdd",
    "playwright": "playwright",
}

# Matches: "- AC1: The endpoint returns 201"
_AC_PATTERN = re.compile(r"^-\s+AC\d+:\s+(.+)$", re.MULTILINE)
# Matches: "# PROT-101 — Add assessment submission endpoint"
_TITLE_PATTERN = re.compile(r"^#\s+\S+\s+—\s+(.+)$", re.MULTILINE)
# Matches: "**Test type**: pytest-bdd"  or  "**Test type**: Playwright"
_TEST_TYPE_PATTERN = re.compile(r"\*\*Test type\*\*:\s+(pytest-bdd|Playwright)", re.IGNORECASE)
# Matches the Description section body up to the next ## heading
_DESC_PATTERN = re.compile(r"## Description\n(.+?)(?=\n##)", re.DOTALL)


def parse_story_text(text: str, story_id: str) -> Story:
    """
    Parse story markdown text into a Story value object.

    Raises ValueError if no acceptance criteria are found.
    Title defaults to story_id when the title heading is absent.
    Description defaults to '' when the Description section is absent.
    test_type defaults to 'playwright' when the Test type field is absent or
    contains an unrecognised value.
    """
    title_m = _TITLE_PATTERN.search(text)
    title = title_m.group(1).strip() if title_m else story_id

    desc_m = _DESC_PATTERN.search(text)
    description = desc_m.group(1).strip() if desc_m else ""

    criteria = _AC_PATTERN.findall(text)
    if not criteria:
        raise ValueError(f"No acceptance criteria found in story {story_id}")

    type_m = _TEST_TYPE_PATTERN.search(text)
    raw_type = type_m.group(1).lower() if type_m else "playwright"
    # Unknown types fall through to the playwright default
    test_type = _TEST_TYPE_MAP.get(raw_type, "playwright")

    return Story(
        id=story_id,
        title=title,
        description=description,
        acceptance_criteria=criteria,
        test_type=test_type,
    )
