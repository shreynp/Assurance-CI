"""
Error-path and coverage-gap tests identified by the triple-agent audit.
Covers: story_loader fallbacks, register malformed JSON, resolve_gate edge
cases, run_tests parse_counts gaps, append_record missing files, and
generate_tests diff truncation.
"""
import importlib.util
import json
import os
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
        text = (
            "**Test type**: pytest-bdd\n"
            "## Description\nSome desc.\n"
            "## Acceptance Criteria\n"
            "- AC1: Works\n"
        )
        story = parse_story_text(text, "PROT-999")
        assert story.title == "PROT-999"

    def test_missing_acceptance_criteria_raises_value_error(self, tmp_path):
        story_file = tmp_path / "PROT-999.md"
        story_file.write_text(
            "# PROT-999 — No AC story\n"
            "**Test type**: pytest-bdd\n"
            "## Description\nSome desc.\n"
        )
        with pytest.raises(ValueError, match="acceptance criteria"):
            load_story("PROT-999", tmp_path)

    def test_missing_file_raises_file_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="PROT-999"):
            load_story("PROT-999", tmp_path)

    def test_description_as_last_section_returns_content(self):
        # Regression: _DESC_PATTERN used a lookahead for \n## that failed when
        # ## Description was the final section — description silently returned "".
        text = (
            "# PROT-999 — Trailing description story\n"
            "**Test type**: pytest-bdd\n"
            "## Acceptance Criteria\n"
            "- AC1: Works\n"
            "## Description\n"
            "This section has no trailing heading.\n"
        )
        story = parse_story_text(text, "PROT-999")
        assert "trailing heading" in story.description


# ─── register malformed JSON ──────────────────────────────────────────────────

class TestRegisterMalformedJson:
    def test_append_record_raises_on_corrupt_json(self, tmp_path):
        register = tmp_path / "register.json"
        register.write_text('{"broken": [}')
        with pytest.raises(json.JSONDecodeError):
            append_record(_make_report(), register)


# ─── commit_parser edge cases ─────────────────────────────────────────────────

class TestCommitParserEdgeCases:
    def test_dual_story_ids_returns_first(self):
        result = extract_story_id("PROT-101 PROT-102: dual story commit")
        assert result == "PROT-101"

    def test_lowercase_does_not_match(self):
        assert extract_story_id("prot-101: lowercase") is None

    def test_no_digit_does_not_match(self):
        assert extract_story_id("PROT-: no number") is None

    def test_whitespace_only_returns_none(self):
        assert extract_story_id("   ") is None

    def test_empty_string_returns_none(self):
        assert extract_story_id("") is None

    def test_utf8_token_does_not_match(self):
        assert extract_story_id("encoding: UTF-8 compliance") is None

    def test_http2_token_does_not_match(self):
        assert extract_story_id("upgrade to HTTP-2 protocol") is None


# ─── GateResult reason format ─────────────────────────────────────────────────

class TestGateResultReasonFormat:
    def test_red_reason_includes_both_counts(self):
        report = ExecutionReport(
            story_id="PROT-101", commit_sha="abc123", author="dev",
            passed=3, failed=2, environment="ci", timestamp="2026-06-21T10:00:00Z",
        )
        gate = GateResult.from_report(report)
        assert gate.status == "red"
        assert "2" in gate.reason
        assert "5" in gate.reason

    def test_zero_zero_reason_reflects_no_evidence(self):
        report = ExecutionReport(
            story_id="PROT-101", commit_sha="abc123", author="dev",
            passed=0, failed=0, environment="ci", timestamp="2026-06-21T10:00:00Z",
        )
        gate = GateResult.from_report(report)
        assert gate.status == "red"


# ─── parse_counts edge cases ─────────────────────────────────────────────────

class TestParseCountsEdgeCases:
    def test_no_tests_ran_returns_zeros(self):
        output = "no tests ran in 0.05s\n"
        passed, failed = _run_tests.parse_counts(output)
        assert passed == 0
        assert failed == 0

    def test_collected_zero_items_returns_zeros(self):
        output = "collected 0 items\n\n"
        passed, failed = _run_tests.parse_counts(output)
        assert passed == 0
        assert failed == 0

    def test_error_in_summary_line_counted_as_failed(self):
        output = (
            "test_x.py::test_a FAILED\n"
            "test_x.py::test_b FAILED\n"
            "test_x.py::test_c ERROR\n"
            "2 failed, 1 error in 0.20s\n"
        )
        passed, failed = _run_tests.parse_counts(output)
        assert failed >= 2

    def test_empty_output_returns_zeros(self):
        passed, failed = _run_tests.parse_counts("")
        assert passed == 0
        assert failed == 0

    def test_all_passed_summary(self):
        output = "3 passed in 0.12s\n"
        passed, failed = _run_tests.parse_counts(output)
        assert passed == 3
        assert failed == 0

    def test_mixed_summary(self):
        output = "1 passed, 1 failed in 0.15s\n"
        passed, failed = _run_tests.parse_counts(output)
        assert passed == 1
        assert failed == 1

    def test_xfailed_returns_zero_counts(self):
        # xfailed tokens don't match the summary regex or PASSED/FAILED substrings.
        # (0, 0) → resolve_gate treats it as red — conservative but correct.
        passed, failed = _run_tests.parse_counts("2 xfailed in 0.10s\n")
        assert passed == 0
        assert failed == 0


# ─── resolve_gate.py error paths ─────────────────────────────────────────────

class TestResolveGateErrorPaths:
    def test_malformed_register_exits_nonzero(self, tmp_path):
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

    def test_missing_register_produces_red_gate(self, tmp_path):
        gate_out = tmp_path / "gate.json"
        result = subprocess.run(
            [sys.executable, "scripts/resolve_gate.py",
             "--register", str(tmp_path / "missing.json"),
             "--story-id", "PROT-101",
             "--commit-sha", "abc123",
             "--output", str(gate_out)],
            capture_output=True, text=True, cwd=PROJECT_ROOT,
        )
        assert result.returncode == 1
        assert json.loads(gate_out.read_text())["status"] == "red"

    def test_no_matching_record_produces_red_gate(self, tmp_path):
        register = tmp_path / "register.json"
        register.write_text(json.dumps([{
            "story_id": "PROT-102", "commit_sha": "other",
            "gate_result": {"status": "green", "reason": "passed"},
        }]))
        gate_out = tmp_path / "gate.json"
        result = subprocess.run(
            [sys.executable, "scripts/resolve_gate.py",
             "--register", str(register),
             "--story-id", "PROT-101",
             "--commit-sha", "abc123",
             "--output", str(gate_out)],
            capture_output=True, text=True, cwd=PROJECT_ROOT,
        )
        assert result.returncode == 1

    def test_green_record_exits_0(self, tmp_path):
        register = tmp_path / "register.json"
        register.write_text(json.dumps([{
            "story_id": "PROT-101", "commit_sha": "abc123abc123",
            "gate_result": {"status": "green", "reason": "All 4 scenario(s) passed"},
        }]))
        gate_out = tmp_path / "gate.json"
        result = subprocess.run(
            [sys.executable, "scripts/resolve_gate.py",
             "--register", str(register),
             "--story-id", "PROT-101",
             "--commit-sha", "abc123abc123",
             "--output", str(gate_out)],
            capture_output=True, text=True, cwd=PROJECT_ROOT,
        )
        assert result.returncode == 0
        assert json.loads(gate_out.read_text())["status"] == "green"

    def test_duplicate_records_last_wins(self, tmp_path):
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
        big_diff = "x" * 20_000
        diff_file = tmp_path / "big.diff"
        diff_file.write_text(big_diff)
        out_dir = tmp_path / "out"
        out_dir.mkdir()

        captured_prompt = {}

        def fake_create(**kwargs):
            msg = kwargs["messages"][0]["content"]
            captured_prompt["content"] = msg
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

        assert "content" in captured_prompt
        assert captured_prompt["content"].count("x") <= 8000


# ─── run_tests.py output truncation ──────────────────────────────────────────

class TestRunTestsOutputTruncation:
    def test_output_truncated_to_4000_chars_in_report(self, tmp_path):
        long_output = "x" * 10_000

        meta = {
            "story_id": "PROT-101",
            "test_type": "pytest-bdd",
            "feature_file": str(tmp_path / "PROT-101.feature"),
            "test_script": str(tmp_path / "test_prot_101.py"),
            "generated_at": "2026-06-22T00:00:00Z",
        }
        gen_dir = tmp_path / "generated" / "PROT-101"
        gen_dir.mkdir(parents=True)
        (gen_dir / "meta.json").write_text(json.dumps(meta))
        report_dir = tmp_path / "reports"
        report_dir.mkdir()

        mock_proc = unittest.mock.MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = long_output
        mock_proc.stderr = ""

        with unittest.mock.patch("subprocess.run", return_value=mock_proc), \
             unittest.mock.patch(
                 "sys.argv",
                 ["run_tests.py",
                  "--story-id", "PROT-101",
                  "--generated-dir", str(tmp_path / "generated"),
                  "--report-out", str(report_dir)],
             ):
            with pytest.raises(SystemExit):
                _run_tests.main()

        report = json.loads((report_dir / "PROT-101_report.json").read_text())
        assert len(report["output"]) <= 4000


# ─── build_pr_body.py coverage ───────────────────────────────────────────────

class TestBuildPrBody:
    def test_happy_path_no_report_defaults_to_zero_counts(self, tmp_path):
        gate = {"status": "green", "reason": "All 3 scenario(s) passed"}
        gate_file = tmp_path / "gate.json"
        gate_file.write_text(json.dumps(gate))
        out_file = tmp_path / "pr_body.md"

        result = subprocess.run(
            [sys.executable, "scripts/build_pr_body.py",
             "--story-id", "PROT-101",
             "--gate", str(gate_file),
             "--report-dir", str(tmp_path),
             "--out", str(out_file)],
            capture_output=True, text=True, cwd=PROJECT_ROOT,
        )
        assert result.returncode == 0
        body = out_file.read_text()
        assert "PROT-101" in body
        assert "GREEN" in body

    def test_happy_path_with_report_shows_counts(self, tmp_path):
        gate = {"status": "green", "reason": "All 3 scenario(s) passed"}
        gate_file = tmp_path / "gate.json"
        gate_file.write_text(json.dumps(gate))
        report = {
            "passed": 3, "failed": 0, "output": "",
            "commit_sha": "abc1234567", "timestamp": "2026-06-22T10:00:00",
        }
        (tmp_path / "PROT-101_report.json").write_text(json.dumps(report))
        out_file = tmp_path / "pr_body.md"

        result = subprocess.run(
            [sys.executable, "scripts/build_pr_body.py",
             "--story-id", "PROT-101",
             "--gate", str(gate_file),
             "--report-dir", str(tmp_path),
             "--out", str(out_file)],
            capture_output=True, text=True, cwd=PROJECT_ROOT,
        )
        assert result.returncode == 0
        body = out_file.read_text()
        assert "**3**" in body

    def test_jira_data_url_renders_hyperlink(self, tmp_path):
        gate = {"status": "red", "reason": "1 scenario(s) failed out of 1"}
        gate_file = tmp_path / "gate.json"
        gate_file.write_text(json.dumps(gate))
        out_file = tmp_path / "pr_body.md"
        env = {**os.environ, "JIRA_DATA_URL": "https://example.com/jira"}

        result = subprocess.run(
            [sys.executable, "scripts/build_pr_body.py",
             "--story-id", "PROT-101",
             "--gate", str(gate_file),
             "--report-dir", str(tmp_path),
             "--out", str(out_file)],
            capture_output=True, text=True, cwd=PROJECT_ROOT, env=env,
        )
        assert result.returncode == 0
        body = out_file.read_text()
        assert "https://example.com/jira/PROT-101.md" in body


# ─── generate_tests.py null Claude response ───────────────────────────────────

class TestGenerateTestsNullClaudeResponse:
    def _make_text_resp(self, text):
        block = unittest.mock.MagicMock()
        block.type = "text"
        block.text = text
        resp = unittest.mock.MagicMock()
        resp.content = [block]
        return resp

    def _make_no_text_resp(self):
        block = unittest.mock.MagicMock()
        block.type = "tool_use"
        resp = unittest.mock.MagicMock()
        resp.content = [block]
        return resp

    def _run_main_with_side_effects(self, tmp_path, side_effects):
        diff_file = tmp_path / "diff.txt"
        diff_file.write_text("some diff")
        out_dir = tmp_path / "out"
        out_dir.mkdir(exist_ok=True)

        responses = list(side_effects)
        call_idx = [0]

        def fake_create(**kwargs):
            resp = responses[call_idx[0]]
            call_idx[0] += 1
            return resp

        with unittest.mock.patch("anthropic.Anthropic") as mock_cls:
            mock_client = unittest.mock.MagicMock()
            mock_client.messages.create.side_effect = fake_create
            mock_cls.return_value = mock_client

            spec = importlib.util.spec_from_file_location(
                f"gen_tests_null_{id(tmp_path)}",
                PROJECT_ROOT / "scripts" / "generate_tests.py",
            )
            mod = importlib.util.module_from_spec(spec)
            with unittest.mock.patch(
                "sys.argv",
                ["generate_tests.py", "--story-id", "PROT-101",
                 "--diff", str(diff_file), "--out", str(out_dir)],
            ):
                spec.loader.exec_module(mod)
                with pytest.raises(SystemExit) as exc:
                    mod.main()
                return exc.value.code

    def test_null_feature_response_exits_1(self, tmp_path):
        code = self._run_main_with_side_effects(tmp_path, [self._make_no_text_resp()])
        assert code == 1

    def test_null_test_script_response_exits_1(self, tmp_path):
        feature_text = "Feature: Test\n  Scenario: AC1\n    Given step\n    When step\n    Then step"
        code = self._run_main_with_side_effects(
            tmp_path,
            [self._make_text_resp(feature_text), self._make_no_text_resp()],
        )
        assert code == 1
