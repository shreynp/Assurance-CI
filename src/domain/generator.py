"""Pure prompt-building and output-parsing functions for AI test generation. No I/O."""
from __future__ import annotations
import re
from .models import Story

_FENCE_RE = re.compile(r"^```[^\n]*\n(.*?)^```", re.DOTALL | re.MULTILINE)

FEATURE_PROMPT_TEMPLATE = """\
You are a test-case author. Given a JIRA story and a code diff, generate a Gherkin (.feature) file \
that covers every acceptance criterion in the story.

Rules:
- One Feature block, titled with the story ID and title.
- One Scenario per acceptance criterion. Name it after the criterion.
- Use Given/When/Then steps that are specific and testable.
- Do NOT add scenarios not backed by acceptance criteria.
- Output ONLY the raw Gherkin text, no markdown fences.

Story ID: {story_id}
Title: {title}
Description:
{description}

Acceptance criteria:
{criteria}

Code diff (for context):
{diff}
"""

PYTEST_BDD_PROMPT_TEMPLATE = """\
You are a Python test-script author. Given a Gherkin feature file and story context, \
write a pytest-bdd test script that implements every step in the feature file.

Rules:
- Use `pytest_bdd` fixtures: `scenarios`, `given`, `when`, `then`.
- The feature file is named exactly `{feature_filename}` — use that exact name in `scenarios()`.
- Target the Next.js API route at BASE_URL (read from env, default http://localhost:3000).
- Use `httpx` for HTTP calls.
- Implement every step — no `pass` placeholders.
- Output ONLY the raw Python code, no markdown fences.

Feature file:
{feature}

Story context:
{description}
"""

PLAYWRIGHT_PROMPT_TEMPLATE = """\
You are a Python test-script author. Given a Gherkin feature file and story context, \
write a Playwright Python test script that implements every scenario.

Rules:
- Use `playwright.sync_api` with `pytest` fixtures (not `pytest-bdd`).
- Each scenario becomes one `test_*` function whose name matches the scenario title.
- Use assertions against the real DOM.
- TARGET_URL read from env (default http://localhost:3000).
- Viewport: 1280x800 for all UI tests.
- Output ONLY the raw Python code, no markdown fences.

Feature file:
{feature}

Story context:
{description}
"""


def build_feature_prompt(story: Story, diff: str) -> str:
    """Return the prompt to send to the model for Gherkin generation."""
    criteria_text = "\n".join(f"- {c}" for c in story.acceptance_criteria)
    return FEATURE_PROMPT_TEMPLATE.format(
        story_id=story.id,
        title=story.title,
        description=story.description,
        criteria=criteria_text,
        diff=diff,
    )


def build_test_script_prompt(story: Story, feature_text: str, feature_filename: str = "") -> str:
    """Return the prompt to send to the model for test-script generation.

    Unknown test_type values silently default to the Playwright template — no error is raised.
    Prompt assumptions baked into the templates:
      pytest-bdd: uses httpx for HTTP calls, BASE_URL env var, no pass placeholders
      playwright:  uses sync_api, TARGET_URL env var, 1280×800 viewport
    """
    if story.test_type == "pytest-bdd":
        return PYTEST_BDD_PROMPT_TEMPLATE.format(
            feature=feature_text,
            description=story.description,
            feature_filename=feature_filename or f"{story.id}.feature",
        )
    # story.test_type == "playwright" — only two valid variants; unknown types also land here
    return PLAYWRIGHT_PROMPT_TEMPLATE.format(
        feature=feature_text,
        description=story.description,
    )


def strip_fences(text: str) -> str:
    """Remove markdown code fences from model output, returning inner content."""
    m = _FENCE_RE.search(text)
    return m.group(1).rstrip("\n") if m else text
