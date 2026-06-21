"""
Tests for the full pipeline — F2 execution parsing, F3 register format,
F4 story-keyed trigger, F5 gate resolution.
All tests are pure-Python with no I/O to external services.
"""
import json
import re
import tempfile
from pathlib import Path

import pytest

from src.domain.commit_parser import extract_story_id, has_story_id
from src.domain.models import ExecutionReport, GateResult, TraceabilityRecord
from src.domain.register import append_record, render_markdown


# ─── F4: Story-keyed pipeline trigger ──────────────────────────────────────

class TestPipelineTrigger:
    """SPEC F4 — commit message parsing drives whether the pipeline runs."""

    # Scenario: developer commits with story ID → pipeline starts
    def test_standard_story_commit_triggers_pipeline(self):
        assert extract_story_id("PROT-101: add assessment submission endpoint") == "PROT-101"

    def test_story_id_extracted_from_pr_title(self):
        assert extract_story_id("PROT-102: add slider to self-assessment") == "PROT-102"

    def test_story_id_extracted_from_prot103(self):
        assert extract_story_id("PROT-103: show delta flags on triangulated view") == "PROT-103"

    # Scenario: no story ID → pipeline skips without error
    def test_no_story_id_skips_pipeline(self):
        assert has_story_id("fix typo in README") is False

    def test_plain_chore_commit_skips(self):
        assert has_story_id("chore: bump version") is False

    def test_whitespace_only_message_skips(self):
        assert has_story_id("   ") is False

    # Scenario: PROT-999 — story file missing → load fails loudly
    def test_missing_story_raises_not_found(self):
        from src.io.story_loader import load_story
        jira_dir = Path(__file__).parent.parent / "jira"
        with pytest.raises(FileNotFoundError, match="PROT-999"):
            load_story("PROT-999", jira_dir)


# ─── F2: Execution output parsing ──────────────────────────────────────────

# Import the parse_counts helper from run_tests (script-level utility)
import importlib.util, sys

def _import_run_tests():
    spec = importlib.util.spec_from_file_location(
        "run_tests",
        Path(__file__).parent.parent / "scripts" / "run_tests.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_run_tests = _import_run_tests()


class TestExecutionOutputParsing:
    """SPEC F2 — execution report records correct pass/fail counts."""

    def test_all_passed(self):
        output = (
            "test_prot_101.py::test_ac1 PASSED\n"
            "test_prot_101.py::test_ac2 PASSED\n"
            "test_prot_101.py::test_ac3 PASSED\n"
            "3 passed in 0.12s\n"
        )
        passed, failed = _run_tests.parse_counts(output)
        assert passed == 3
        assert failed == 0

    def test_some_failed(self):
        output = (
            "test_prot_101.py::test_ac1 PASSED\n"
            "test_prot_101.py::test_ac2 FAILED\n"
            "1 passed, 1 failed in 0.15s\n"
        )
        passed, failed = _run_tests.parse_counts(output)
        assert passed == 1
        assert failed == 1

    def test_all_failed(self):
        output = (
            "test_prot_101.py::test_ac1 FAILED\n"
            "test_prot_101.py::test_ac2 FAILED\n"
            "2 failed in 0.10s\n"
        )
        passed, failed = _run_tests.parse_counts(output)
        assert failed == 2

    def test_error_counts_as_failed(self):
        output = "test_prot_101.py::test_ac1 ERROR\n"
        passed, failed = _run_tests.parse_counts(output)
        assert failed >= 1

    def test_empty_output_returns_zeros(self):
        passed, failed = _run_tests.parse_counts("")
        assert passed == 0
        assert failed == 0


# ─── F3: Traceability register format ──────────────────────────────────────

class TestTraceabilityRegisterFormat:
    """SPEC F3 — register has correct table columns and append-only behaviour."""

    def _make_report(self, story_id="PROT-101", sha="abc1234567", passed=3, failed=0):
        return ExecutionReport(
            story_id=story_id,
            commit_sha=sha,
            author="dev@example.com",
            passed=passed,
            failed=failed,
            environment="ci",
            timestamp="2026-06-21T10:00:00Z",
        )

    def _make_record(self, story_id="PROT-101", sha="abc1234567", passed=3, failed=0):
        report = self._make_report(story_id=story_id, sha=sha, passed=passed, failed=failed)
        gate = GateResult.from_report(report)
        return TraceabilityRecord(
            story_id=story_id,
            commit_sha=sha,
            author="dev@example.com",
            feature_file_path=f"generated/{story_id}/{story_id}.feature",
            test_script_path=f"generated/{story_id}/test_{story_id.lower().replace('-','_')}.py",
            execution_report=report,
            gate_result=gate,
            appended_at="2026-06-21T10:00:00Z",
        )

    # Scenario: register has the required columns
    def test_register_table_has_required_columns(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "register.json"
            append_record(self._make_record(), path)
            md = render_markdown(path)
            assert "Story" in md
            assert "Commit" in md
            assert "Author" in md
            assert "Result" in md
            assert "Date" in md

    # Scenario: register shows story ID, SHA, author, result, date
    def test_register_row_contains_story_id(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "register.json"
            append_record(self._make_record(story_id="PROT-101", sha="abc1234567"), path)
            md = render_markdown(path)
            assert "PROT-101" in md
            assert "abc1234" in md   # 7-char SHA in the rendered table
            assert "dev@example.com" in md
            assert "2026-06-21" in md

    # Scenario: green result shows GREEN
    def test_register_green_result_shown(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "register.json"
            append_record(self._make_record(passed=3, failed=0), path)
            md = render_markdown(path)
            assert "GREEN" in md

    # Scenario: red result shows RED
    def test_register_red_result_shown(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "register.json"
            append_record(self._make_record(passed=2, failed=1), path)
            md = render_markdown(path)
            assert "RED" in md

    # Scenario: exactly one new row appended per run, prior rows unchanged
    def test_append_only_one_row_per_run(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "register.json"
            append_record(self._make_record(story_id="PROT-101"), path)
            records_before = json.loads(path.read_text())
            append_record(self._make_record(story_id="PROT-102"), path)
            records_after = json.loads(path.read_text())
            assert len(records_after) == len(records_before) + 1
            # Prior row unchanged
            assert records_after[0] == records_before[0]

    # Scenario: 3 stories produce 3 independent rows
    def test_all_three_seed_stories_in_register(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "register.json"
            for sid in ("PROT-101", "PROT-102", "PROT-103"):
                append_record(self._make_record(story_id=sid), path)
            records = json.loads(path.read_text())
            assert len(records) == 3
            ids = [r["story_id"] for r in records]
            assert "PROT-101" in ids
            assert "PROT-102" in ids
            assert "PROT-103" in ids


# ─── F5: Deploy gate ────────────────────────────────────────────────────────

class TestDeployGate:
    """SPEC F5 — gate is green when all pass, red when any fail."""

    # Scenario: all scenarios passed → green gate
    def test_gate_green_when_all_passed(self):
        report = ExecutionReport(
            story_id="PROT-101", commit_sha="sha001", author="dev",
            passed=4, failed=0, environment="ci", timestamp="2026-06-21T10:00:00Z",
        )
        gate = GateResult.from_report(report)
        assert gate.status == "green"

    # Scenario: at least one scenario failed → red gate
    def test_gate_red_when_one_fails(self):
        report = ExecutionReport(
            story_id="PROT-102", commit_sha="sha002", author="dev",
            passed=4, failed=1, environment="ci", timestamp="2026-06-21T10:00:00Z",
        )
        gate = GateResult.from_report(report)
        assert gate.status == "red"

    def test_gate_red_when_all_fail(self):
        report = ExecutionReport(
            story_id="PROT-103", commit_sha="sha003", author="dev",
            passed=0, failed=3, environment="ci", timestamp="2026-06-21T10:00:00Z",
        )
        gate = GateResult.from_report(report)
        assert gate.status == "red"

    # Edge: zero tests run is treated as red (no evidence of passing)
    def test_gate_red_when_zero_tests_ran(self):
        report = ExecutionReport(
            story_id="PROT-101", commit_sha="sha004", author="dev",
            passed=0, failed=0, environment="ci", timestamp="2026-06-21T10:00:00Z",
        )
        gate = GateResult.from_report(report)
        assert gate.status == "red"

    # Reason string is present
    def test_gate_green_reason_mentions_count(self):
        report = ExecutionReport(
            story_id="PROT-101", commit_sha="sha005", author="dev",
            passed=4, failed=0, environment="ci", timestamp="2026-06-21T10:00:00Z",
        )
        gate = GateResult.from_report(report)
        assert "4" in gate.reason

    def test_gate_red_reason_mentions_failed_count(self):
        report = ExecutionReport(
            story_id="PROT-102", commit_sha="sha006", author="dev",
            passed=3, failed=2, environment="ci", timestamp="2026-06-21T10:00:00Z",
        )
        gate = GateResult.from_report(report)
        assert "2" in gate.reason

    # resolve_gate.py script integration
    def test_resolve_gate_script_exits_0_on_green(self):
        import subprocess, sys
        with tempfile.TemporaryDirectory() as tmpdir:
            register = Path(tmpdir) / "register.json"
            # Write a green record directly
            record = {
                "story_id": "PROT-101",
                "commit_sha": "abc123abc123",
                "author": "dev",
                "gate_result": {"status": "green", "reason": "All 4 scenario(s) passed"},
                "appended_at": "2026-06-21T10:00:00Z",
            }
            register.write_text(json.dumps([record]))
            gate_out = Path(tmpdir) / "gate.json"
            result = subprocess.run(
                [sys.executable, "scripts/resolve_gate.py",
                 "--register", str(register),
                 "--story-id", "PROT-101",
                 "--commit-sha", "abc123abc123",
                 "--output", str(gate_out)],
                capture_output=True, text=True,
            )
            assert result.returncode == 0
            assert json.loads(gate_out.read_text())["status"] == "green"

    def test_resolve_gate_script_exits_1_on_red(self):
        import subprocess, sys
        with tempfile.TemporaryDirectory() as tmpdir:
            register = Path(tmpdir) / "register.json"
            record = {
                "story_id": "PROT-102",
                "commit_sha": "def456def456",
                "author": "dev",
                "gate_result": {"status": "red", "reason": "1 scenario(s) failed out of 5"},
                "appended_at": "2026-06-21T10:00:00Z",
            }
            register.write_text(json.dumps([record]))
            gate_out = Path(tmpdir) / "gate.json"
            result = subprocess.run(
                [sys.executable, "scripts/resolve_gate.py",
                 "--register", str(register),
                 "--story-id", "PROT-102",
                 "--commit-sha", "def456def456",
                 "--output", str(gate_out)],
                capture_output=True, text=True,
            )
            assert result.returncode == 1
            assert json.loads(gate_out.read_text())["status"] == "red"
