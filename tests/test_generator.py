"""Tests for src/domain/generator.py — pure prompt-building, no API calls."""
from pathlib import Path

import pytest

from src.domain.generator import (
    build_feature_prompt,
    build_test_script_prompt,
    strip_fences,
)
from src.io.story_loader import load_story

JIRA_DIR = Path(__file__).parent.parent / "jira"


# --- strip_fences ---

class TestStripFences:
    def test_removes_gherkin_fence(self):
        raw = "```gherkin\nFeature: F\n  Scenario: S\n```"
        assert strip_fences(raw) == "Feature: F\n  Scenario: S"

    def test_removes_python_fence(self):
        raw = "```python\ndef test_foo():\n    pass\n```"
        assert strip_fences(raw) == "def test_foo():\n    pass"

    def test_passthrough_when_no_fence(self):
        raw = "Feature: No fences here"
        assert strip_fences(raw) == raw

    def test_empty_fence_returns_empty(self):
        raw = "```\n\n```"
        assert strip_fences(raw) == ""


# --- build_feature_prompt (F1) ---

class TestBuildFeaturePrompt:
    def setup_method(self):
        self.story = load_story("PROT-101", JIRA_DIR)
        self.prompt = build_feature_prompt(self.story, "diff content here")

    def test_contains_story_id(self):
        assert "PROT-101" in self.prompt

    def test_contains_title(self):
        assert self.story.title in self.prompt

    def test_contains_all_acceptance_criteria(self):
        for ac in self.story.acceptance_criteria:
            assert ac in self.prompt

    def test_contains_diff(self):
        assert "diff content here" in self.prompt

    def test_instructs_gherkin_only(self):
        assert "no markdown fences" in self.prompt.lower() or "raw Gherkin" in self.prompt

    def test_feature_prompt_for_prot102(self):
        story = load_story("PROT-102", JIRA_DIR)
        prompt = build_feature_prompt(story, "")
        assert "PROT-102" in prompt
        assert len([c for c in story.acceptance_criteria if c in prompt]) == len(story.acceptance_criteria)


# --- build_test_script_prompt (F1) ---

class TestBuildTestScriptPrompt:
    FEATURE_TEXT = "Feature: PROT-101\n  Scenario: AC1\n    Given...\n    When...\n    Then..."

    def test_pytest_bdd_prompt_for_pytest_bdd_story(self):
        story = load_story("PROT-101", JIRA_DIR)  # test_type=pytest-bdd
        prompt = build_test_script_prompt(story, self.FEATURE_TEXT)
        assert "pytest_bdd" in prompt
        assert "httpx" in prompt
        assert self.FEATURE_TEXT in prompt

    def test_playwright_prompt_for_ui_story(self):
        story = load_story("PROT-102", JIRA_DIR)  # test_type=playwright
        prompt = build_test_script_prompt(story, self.FEATURE_TEXT)
        assert "playwright" in prompt.lower()
        assert "1280x800" in prompt or "1280" in prompt
        assert self.FEATURE_TEXT in prompt

    def test_pytest_bdd_prompt_does_not_mention_playwright(self):
        story = load_story("PROT-101", JIRA_DIR)
        prompt = build_test_script_prompt(story, self.FEATURE_TEXT)
        # Should be pytest-bdd, not playwright
        assert "playwright" not in prompt.lower()

    def test_playwright_prompt_does_not_mention_pytest_bdd(self):
        story = load_story("PROT-102", JIRA_DIR)
        prompt = build_test_script_prompt(story, self.FEATURE_TEXT)
        assert "pytest_bdd" not in prompt

    def test_instructs_no_pass_placeholders(self):
        story = load_story("PROT-101", JIRA_DIR)
        prompt = build_test_script_prompt(story, self.FEATURE_TEXT)
        assert "pass" in prompt  # the rule says "no `pass` placeholders"

    def test_prompt_contains_story_description(self):
        story = load_story("PROT-101", JIRA_DIR)
        prompt = build_test_script_prompt(story, self.FEATURE_TEXT)
        assert "assessment" in prompt.lower()  # description mentions assessments


# --- property: prompt never empty ---

class TestPromptProperties:
    """Invariants that must hold for any story."""

    @pytest.mark.parametrize("story_id", ["PROT-101", "PROT-102", "PROT-103"])
    def test_feature_prompt_always_non_empty(self, story_id):
        story = load_story(story_id, JIRA_DIR)
        prompt = build_feature_prompt(story, "")
        assert len(prompt) > 100

    @pytest.mark.parametrize("story_id", ["PROT-101", "PROT-102", "PROT-103"])
    def test_test_script_prompt_always_non_empty(self, story_id):
        story = load_story(story_id, JIRA_DIR)
        prompt = build_test_script_prompt(story, "Feature: X")
        assert len(prompt) > 100

    @pytest.mark.parametrize("story_id", ["PROT-101", "PROT-102", "PROT-103"])
    def test_feature_prompt_contains_all_criteria(self, story_id):
        story = load_story(story_id, JIRA_DIR)
        prompt = build_feature_prompt(story, "")
        for ac in story.acceptance_criteria:
            assert ac in prompt, f"Criterion missing from prompt: {ac}"
