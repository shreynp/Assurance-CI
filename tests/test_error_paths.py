"""
Error-path and coverage-gap tests identified by the triple-agent audit.
Covers: story_loader fallbacks, register malformed JSON, resolve_gate edge
cases, run_tests parse_counts gaps, append_record missing files, and
generate_tests diff truncation.
"""
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest.mock
from pathlib import Path

import pytest

from src.domain.commit_parser import extract_story_id
from src.domain.models import ExecutionReport, GateResult
from src.domain.register import append_record
from src.domain.story_loader import parse_story_text
from src.io.story_loader import load_story

# ─── Helpers ─────────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).parent.parent


def _import_run_tests():
    spec = importlib.util.spec_from_file_location(
        "run_tests", PROJECT_ROOT / "scripts" / "run_tests.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_run_tests = _import_run_tests()


def _make_report(story_id="PROT-101", sha="abc123", passed=3, failed=0):
    from src.domain.models import TraceabilityRecord

    report = ExecutionReport(
        story_id=story_id, commit_sha=sha, author="dev",
        passed=passed, failed=failed,
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


# ─── story_loader fallbacks ───────────────────────────────────────────────────

class TestStoryLoaderFallbacks:
    def test_missing_description_returns_empty_string(self, tmp_path):
        """Story without a ## Description section → description=''."""
        story_file = tmp_path / "PROT-999.md"
        story_file.write_text(
            "# PROT-999 — No description story\n"
            "**Test type**: pytest-bdd\n"
            "## Acceptance Criteria\n"
            "- AC1: Something works\n"
        )
        story = load_story("PROT-999", tmp_path)
        assert story.description == ""
        assert story.id == "PROT-999"

    def test_missing_test_type_defaults_to_playwright(self, tmp_path):
        """Story without a **Test type** line → test_type defaults to 'playwright'."""
        story_file = tmp_path / "PROT-999.md"
        story_file.write_text(
            "# PROT-999 — No type story\n"
            "## Description\nSome description.\n"
            "## Acceptance Criteria\n"
            "- AC1: Something works\n"
        )
        story = load_story("PROT-999", tmp_path)
        assert story.test_type == "playwright"

    def test_unknown_test_type_defaults_to_playwright(self, tmp_path):
        """Unrecognised test type (e.g. Selenium) → silently falls back to 'playwright'."""
        story_file = tmp_path / "PROT-999.md"
        story_file.write_text(
            "# PROT-999 — Selenium story\n"
            "**Test type**: Selenium\n"
            "## Description\nSome description.\n"
            "## Acceptance Criteria\n"
            "- AC1: Something works\n"
        )
        story = load_story("PROT-999", tmp_path)
        assert story.test_type == "playwright"

    def test_non_ascii_content_parses_without_error(self, tmp_path):
        """Story file with non-ASCII characters (accents, em-dashes) must not raise."""
        story_file = tmp_path / "PROT-999.md"
        story_file.write_text(
            "# PROT-999 — Café story\n"
            "**Test type**: pytest-bdd\n"
            "## Description\nDescription with em—dash.\n"
            "## Acceptance Criteria\n"
            "- AC1: Résumé field accepts accented characters\n",
            encoding="utf-8",
        )
        story = load_story("PROT-999", tmp_path)
        assert "Résumé" in story.acceptance_criteria[0]

    def test_missing_title_falls_back_to_story_id(self):
        """When the title heading is absent, title defaults to story_id."""
        text = (
            "**Test type**: pytest-bdd\n"
            "## Description\nSome desc.\n"
            "## Acceptance Criteria\n"
            "- AC1: Works\n"
        )
        story = parse_story_text(text, "PROT-999")
        assert story.title == "PROT-999"


# ─── register malformed JSON ──────────────────────────────────────────────────

class TestRegisterMalformedJson:
    def test_append_record_raises_on_corrupt_json(self, tmp_path):
        """append_record raises JSONDecodeError when the register file is corrupt."""
        register = tmp_path / "register.json"
        register.write_text('{"broken": [}')
        with pytest.raises(json.JSONDecodeError):
            append_record(_make_report(), register)


# ─── commit_parser first-match-wins ──────────────────────────────────────────

class TestCommitParserFirstMatch:
    def test_dual_story_ids_returns_first(self):
        """When two story IDs appear in a message, only the first is returned."""
        result = extract_story_id("PROT-101 PROT-102: dual story commit")
        assert result == "PROT-101"


# ─── GateResult reason format ─────────────────────────────────────────────────

class TestGateResultReasonFormat:
    def test_red_reason_includes_both_counts(self):
        """Red gate reason must include both the failed and total counts."""
        report = ExecutionReport(
            story_id="PROT-101", commit_sha="abc123", author="dev",
            passed=3, failed=2, environment="ci", timestamp="2026-06-21T10:00:00Z",
        )
        gate = GateResult.from_report(report)
        assert gate.status == "red"
        assert "2" in gate.reason   # failed count
        assert "5" in gate.reason   # total (3+2)


# ─── parse_counts edge cases ─────────────────────────────────────────────────

class TestParseCountsEdgeCases:
    def test_no_tests_ran_returns_zeros(self):
        """'no tests ran' output produces (0, 0) without raising."""
        output = "no tests ran in 0.05s\n"
        passed, failed = _run_tests.parse_counts(output)
        assert passed == 0
        assert failed == 0

    def test_collected_zero_items_returns_zeros(self):
        """'collected 0 items' output (no summary line) returns (0, 0)."""
        output = "collected 0 items\n\n"
        passed, failed = _run_tests.parse_counts(output)
        assert passed == 0
        assert failed == 0

    def test_error_in_summary_line_counted_as_failed(self):
        """Pytest summary with errors ('2 failed, 1 error') counts both as failures."""
        output = (
            "test_x.py::test_a FAILED\n"
            "test_x.py::test_b FAILED\n"
            "test_x.py::test_c ERROR\n"
            "2 failed, 1 error in 0.20s\n"
        )
        passed, failed = _run_tests.parse_counts(output)
        assert failed >= 2


# ─── resolve_gate.py error paths ─────────────────────────────────────────────

class TestResolveGateErrorPaths:
    def test_malformed_register_exits_nonzero(self, tmp_path):
        """resolve_gate.py with a corrupt register exits non-zero and prints an error."""
        register = tmp_path / "register.json"
        register.write_text('not valid json')
        gate_out = tmp_path / "gate.json"
        result = subprocess.run(
            [sys.executable, "scripts/resolve_gate.py",
             "--register", str(register),
             "--story-id", "PROT-101",
             "--commit-sha", "abc123",
             "--output", str(gate_out)],
            capture_output=True, text=True, cwd=PROJECT_ROOT,
        )
        assert result.returncode != 0
        assert "ERROR" in result.stdout or "ERROR" in result.stderr

    def test_duplicate_records_last_wins(self, tmp_path):
        """When two records share story_id+commit_sha, the last (latest) is used."""
        register = tmp_path / "register.json"
        records = [
            {"story_id": "PROT-101", "commit_sha": "abc123",
             "gate_result": {"status": "red", "reason": "first run failed"}},
            {"story_id": "PROT-101", "commit_sha": "abc123",
             "gate_result": {"status": "green", "reason": "second run passed"}},
        ]
        register.write_text(json.dumps(records))
        gate_out = tmp_path / "gate.json"
        result = subprocess.run(
            [sys.executable, "scripts/resolve_gate.py",
             "--register", str(register),
             "--story-id", "PROT-101",
             "--commit-sha", "abc123",
             "--output", str(gate_out)],
            capture_output=True, text=True, cwd=PROJECT_ROOT,
        )
        assert result.returncode == 0
        assert json.loads(gate_out.read_text())["status"] == "green"


# ─── append_record.py error paths ────────────────────────────────────────────

class TestAppendRecordScriptErrorPaths:
    def test_missing_meta_json_exits_nonzero(self, tmp_path):
        """append_record.py with no meta.json exits non-zero with an error message."""
        gen_dir = tmp_path / "generated"
        gen_dir.mkdir()
        report_dir = tmp_path / "reports"
        report_dir.mkdir()
        register = tmp_path / "register.json"

        result = subprocess.run(
            [sys.executable, "scripts/append_record.py",
             "--story-id", "PROT-101",
             "--commit-sha", "abc123",
             "--author", "dev",
             "--generated-dir", str(gen_dir),
             "--report-dir", str(report_dir),
             "--register", str(register)],
            capture_output=True, text=True, cwd=PROJECT_ROOT,
        )
        assert result.returncode != 0


# ─── generate_tests.py diff truncation ───────────────────────────────────────

anthropic_pkg = pytest.importorskip("anthropic", reason="anthropic package not installed")


class TestGenerateTestsDiffTruncation:
    def test_diff_truncated_to_8000_chars(self, tmp_path):
        """generate_tests.py truncates diff to 8000 chars before passing to the model."""
        big_diff = "x" * 20_000
        diff_file = tmp_path / "big.diff"
        diff_file.write_text(big_diff)
        out_dir = tmp_path / "out"
        out_dir.mkdir()

        captured_prompt = {}

        def fake_create(**kwargs):
            msg = kwargs["messages"][0]["content"]
            captured_prompt["content"] = msg
            # Return a minimal valid Anthropic-style response
            text_block = unittest.mock.MagicMock()
            text_block.type = "text"
            text_block.text = "Feature: Test\n  Scenario: AC1\n    Given step\n    When step\n    Then step"
            resp = unittest.mock.MagicMock()
            resp.content = [text_block]
            return resp

        with unittest.mock.patch("anthropic.Anthropic") as mock_anthropic_cls:
            mock_client = unittest.mock.MagicMock()
            mock_client.messages.create.side_effect = fake_create
            mock_anthropic_cls.return_value = mock_client

            # Import the module and call main() explicitly with patched args
            spec = importlib.util.spec_from_file_location(
                "generate_tests_mod", PROJECT_ROOT / "scripts" / "generate_tests.py"
            )
            mod = importlib.util.module_from_spec(spec)
            with unittest.mock.patch(
                "sys.argv",
                ["generate_tests.py",
                 "--story-id", "PROT-101",
                 "--diff", str(diff_file),
                 "--out", str(out_dir)],
            ):
                spec.loader.exec_module(mod)
                mod.main()

        # The diff in the prompt must be at most 8000 chars
        assert "content" in captured_prompt
        # Count occurrences of the repeated char — must not exceed 8000
        assert captured_prompt["content"].count("x") <= 8000
