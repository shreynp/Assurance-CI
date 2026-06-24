"""Core domain value objects — pure data, no I/O."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class Story:
    """A parsed JIRA story with acceptance criteria and test type."""

    id: str          # e.g. "PROT-101"
    title: str
    description: str
    acceptance_criteria: list[str]
    test_type: Literal["pytest-bdd", "playwright"]


@dataclass(frozen=True)
class Commit:
    """A git commit with its associated diff and optional story reference.

    Defined for future use (Phase 1 batch processing); not used by the current pipeline.
    """

    sha: str
    author: str
    message: str
    story_id: str | None  # None when no story ID found in message
    diff: str


@dataclass(frozen=True)
class FeatureFile:
    """AI-generated Gherkin feature file for a story+commit pair."""

    story_id: str
    commit_sha: str
    gherkin_content: str
    generated_at: str   # ISO-8601


@dataclass(frozen=True)
class TestScript:
    """AI-generated test script (pytest-bdd or Playwright) for a feature file."""

    story_id: str
    commit_sha: str
    test_type: Literal["pytest-bdd", "playwright"]
    content: str
    generated_at: str   # ISO-8601


@dataclass
class ExecutionReport:
    """Raw output from running the generated test script."""

    story_id: str
    commit_sha: str
    author: str
    passed: int
    failed: int
    environment: str
    timestamp: str      # ISO-8601
    output: str = ""

    @property
    def all_passed(self) -> bool:
        """True only when passed > 0 and failed == 0; (0, 0) is treated as red to prevent false-green gates with no test evidence."""
        return self.failed == 0 and self.passed > 0


@dataclass(frozen=True)
class GateResult:
    """Deploy gate decision derived from an ExecutionReport."""

    status: Literal["green", "red"]
    reason: str

    @classmethod
    def from_report(cls, report: ExecutionReport) -> "GateResult":
        """
        Derive a gate decision from an ExecutionReport.

        Red-gate triggers:
          1. report.all_passed is False (zero passed, or any failed — see ExecutionReport.all_passed)
          2. Zero passed with zero failed counts as red — an empty run cannot be evidence of passing.
        """
        if report.all_passed:
            return cls(status="green", reason=f"All {report.passed} scenario(s) passed")
        return cls(
            status="red",
            reason=f"{report.failed} scenario(s) failed out of {report.passed + report.failed}",
        )


@dataclass
class TraceabilityRecord:
    """Full evidence record written to the register after each pipeline run."""

    story_id: str
    commit_sha: str
    author: str
    feature_file_path: str
    test_script_path: str
    execution_report: ExecutionReport
    gate_result: GateResult
    appended_at: str    # ISO-8601
