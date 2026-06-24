"""Unit tests for pure domain logic — no I/O, no Claude calls."""
import json
import tempfile
from pathlib import Path

import pytest

from src.domain.commit_parser import extract_story_id, has_story_id
from src.domain.models import ExecutionReport, GateResult
from src.domain.register import append_record, render_markdown
from src.io.story_loader import load_story

# --- commit_parser ---

class TestExtractStoryId:
    def test_standard_prefix_colon(self):
        assert extract_story_id("PROT-101: add assessment endpoint") == "PROT-101"

    def test_story_id_mid_message(self):
        assert extract_story_id("fix PROT-202 broken slider") == "PROT-202"

    def test_no_story_id_returns_none(self):
        assert extract_story_id("fix typo in README") is None

    def test_has_story_id_true(self):
        assert has_story_id("PROT-101: something") is True

    def test_has_story_id_false(self):
        assert has_story_id("chore: bump version") is False

    def test_does_not_match_utf8(self):
        assert extract_story_id("encoding: UTF-8 support") is None

    def test_does_not_match_http2(self):
        assert extract_story_id("upgrade to HTTP-2") is None


# --- GateResult domain logic ---

class TestGateResult:
    def test_green_when_all_passed(self):
        report = ExecutionReport(
            story_id="PROT-101", commit_sha="abc123", author="dev",
            passed=3, failed=0, environment="ci", timestamp="2026-06-21T10:00:00Z",
        )
        gate = GateResult.from_report(report)
        assert gate.status == "green"

    def test_red_when_any_failed(self):
        report = ExecutionReport(
            story_id="PROT-101", commit_sha="abc123", author="dev",
            passed=2, failed=1, environment="ci", timestamp="2026-06-21T10:00:00Z",
        )
        gate = GateResult.from_report(report)
        assert gate.status == "red"

    def test_red_when_zero_passed(self):
        report = ExecutionReport(
            story_id="PROT-101", commit_sha="abc123", author="dev",
            passed=0, failed=0, environment="ci", timestamp="2026-06-21T10:00:00Z",
        )
        gate = GateResult.from_report(report)
        assert gate.status == "red"

    def test_all_passed_property_true(self):
        report = ExecutionReport(
            story_id="PROT-101", commit_sha="abc123", author="dev",
            passed=3, failed=0, environment="ci", timestamp="2026-06-21T10:00:00Z",
        )
        assert report.all_passed is True

    def test_all_passed_property_false_when_failed(self):
        report = ExecutionReport(
            story_id="PROT-101", commit_sha="abc123", author="dev",
            passed=0, failed=1, environment="ci", timestamp="2026-06-21T10:00:00Z",
        )
        assert report.all_passed is False

    def test_all_passed_property_false_when_zero_zero(self):
        report = ExecutionReport(
            story_id="PROT-101", commit_sha="abc123", author="dev",
            passed=0, failed=0, environment="ci", timestamp="2026-06-21T10:00:00Z",
        )
        assert report.all_passed is False

    def test_green_reason_mentions_count(self):
        report = ExecutionReport(
            story_id="PROT-101", commit_sha="abc123", author="dev",
            passed=4, failed=0, environment="ci", timestamp="2026-06-21T10:00:00Z",
        )
        gate = GateResult.from_report(report)
        assert "4" in gate.reason

    def test_red_reason_mentions_failed_and_total(self):
        report = ExecutionReport(
            story_id="PROT-101", commit_sha="abc123", author="dev",
            passed=3, failed=2, environment="ci", timestamp="2026-06-21T10:00:00Z",
        )
        gate = GateResult.from_report(report)
        assert "2" in gate.reason
        assert "5" in gate.reason


# --- story_loader ---

class TestStoryLoader:
    def test_loads_prot101(self):
        jira_dir = Path(__file__).parent.parent / "jira"
        story = load_story("PROT-101", jira_dir)
        assert story.id == "PROT-101"
        assert story.test_type == "pytest-bdd"
        assert len(story.acceptance_criteria) == 6

    def test_loads_prot102(self):
        jira_dir = Path(__file__).parent.parent / "jira"
        story = load_story("PROT-102", jira_dir)
        assert story.test_type == "playwright"
        assert len(story.acceptance_criteria) == 6

    def test_missing_story_raises(self):
        jira_dir = Path(__file__).parent.parent / "jira"
        with pytest.raises(FileNotFoundError, match="PROT-999"):
            load_story("PROT-999", jira_dir)


# --- register ---

class TestRegister:
    def _make_record(self, story_id="PROT-101", sha="abc1234", status="green"):
        from src.domain.models import TraceabilityRecord
        report = ExecutionReport(
            story_id=story_id, commit_sha=sha, author="dev",
            passed=3, failed=0 if status == "green" else 1,
            environment="ci", timestamp="2026-06-21T10:00:00Z",
        )
        gate = GateResult.from_report(report)
        return TraceabilityRecord(
            story_id=story_id, commit_sha=sha, author="dev",
            feature_file_path=f"generated/{story_id}/test.feature",
            test_script_path=f"generated/{story_id}/test_script.py",
            execution_report=report,
            gate_result=gate,
            appended_at="2026-06-21T10:00:00Z",
        )

    def test_append_creates_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "register.json"
            record = self._make_record()
            append_record(record, path)
            assert path.exists()
            data = json.loads(path.read_text())
            assert len(data) == 1
            assert data[0]["story_id"] == "PROT-101"

    def test_append_is_additive(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "register.json"
            append_record(self._make_record(story_id="PROT-101"), path)
            append_record(self._make_record(story_id="PROT-102"), path)
            data = json.loads(path.read_text())
            assert len(data) == 2

    def test_render_markdown_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "register.json"
            md = render_markdown(path)
            assert "No traceability records" in md

    def test_render_markdown_has_table(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "register.json"
            append_record(self._make_record(), path)
            md = render_markdown(path)
            assert "PROT-101" in md
            assert "GREEN" in md

    def test_render_markdown_sha_truncated(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "register.json"
            append_record(self._make_record(sha="abc1234567890"), path)
            md = render_markdown(path)
            assert "abc1234" in md
            assert "abc1234567890" not in md

    def test_render_markdown_red_record(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "register.json"
            append_record(self._make_record(status="red"), path)
            md = render_markdown(path)
            assert "RED" in md
