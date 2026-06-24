"""Unit tests for scripts/build_context.py — mocks subprocess, no git required."""
from __future__ import annotations

import subprocess
import sys
import textwrap
from unittest.mock import patch

sys.path.insert(0, ".")

from scripts.build_context import (
    build,
    changed_files,
    changed_symbols,
    context_type,
    find_callers,
)

# ---------------------------------------------------------------------------
# changed_files
# ---------------------------------------------------------------------------

class TestChangedFiles:
    def test_returns_list_of_changed_files(self):
        with patch("scripts.build_context._run_git") as mock_git:
            mock_git.return_value = "src/domain/models.py\nsrc/domain/register.py\n"
            result = changed_files("HEAD~1", "HEAD")
        assert result == ["src/domain/models.py", "src/domain/register.py"]

    def test_empty_diff_returns_empty_list(self):
        with patch("scripts.build_context._run_git") as mock_git:
            mock_git.return_value = ""
            result = changed_files("HEAD~1", "HEAD")
        assert result == []

    def test_git_error_returns_empty_list(self):
        """CalledProcessError (e.g. no parent commit) → empty list, no crash."""
        with patch("scripts.build_context._run_git") as mock_git:
            mock_git.side_effect = subprocess.CalledProcessError(128, "git diff")
            result = changed_files("HEAD~1", "HEAD")
        assert result == []

    def test_strips_blank_lines(self):
        with patch("scripts.build_context._run_git") as mock_git:
            mock_git.return_value = "src/a.py\n\n"
            result = changed_files("HEAD~1", "HEAD")
        assert result == ["src/a.py"]


# ---------------------------------------------------------------------------
# changed_symbols
# ---------------------------------------------------------------------------

class TestChangedSymbols:
    def test_detects_changed_function_name(self, tmp_path):
        py_file = tmp_path / "models.py"
        py_file.write_text(textwrap.dedent("""\
            def append_record(x):
                pass

            def render_markdown(x):
                pass
        """))
        diff = textwrap.dedent("""\
            +def append_record(x):
            +    pass
        """)
        with patch("scripts.build_context._run_git", return_value=diff):
            result = changed_symbols(str(py_file), "HEAD~1", "HEAD")
        assert "append_record" in result

    def test_ignores_non_python_files(self, tmp_path):
        txt_file = tmp_path / "README.md"
        txt_file.write_text("# Readme")
        with patch("scripts.build_context._run_git", return_value="+some diff"):
            result = changed_symbols(str(txt_file), "HEAD~1", "HEAD")
        assert result == []

    def test_git_error_returns_empty(self, tmp_path):
        py_file = tmp_path / "x.py"
        py_file.write_text("def foo(): pass\n")
        with patch("scripts.build_context._run_git") as mock_git:
            mock_git.side_effect = subprocess.CalledProcessError(128, "git diff")
            result = changed_symbols(str(py_file), "HEAD~1", "HEAD")
        assert result == []

    def test_missing_file_returns_empty(self):
        with patch("scripts.build_context._run_git", return_value="+def foo():"):
            result = changed_symbols("/nonexistent/file.py", "HEAD~1", "HEAD")
        assert result == []


# ---------------------------------------------------------------------------
# find_callers — fixture: two files where one imports the other
# ---------------------------------------------------------------------------

class TestFindCallers:
    def test_detects_direct_importer(self, tmp_path, monkeypatch):
        # module_a.py defines something; module_b.py imports it
        module_a = tmp_path / "module_a.py"
        module_a.write_text("def do_thing(): pass\n")

        module_b = tmp_path / "module_b.py"
        module_b.write_text("from module_a import do_thing\n")

        # Make find_callers search tmp_path instead of real src/scripts
        import scripts.build_context as bc
        monkeypatch.setattr(bc, "_SEARCH_ROOTS", (str(tmp_path),))

        result = find_callers([str(module_a)])
        assert str(module_b) in result
        assert "do_thing" in result[str(module_b)]

    def test_changed_file_not_listed_as_its_own_caller(self, tmp_path, monkeypatch):
        module_a = tmp_path / "module_a.py"
        module_a.write_text("def do_thing(): pass\n")

        import scripts.build_context as bc
        monkeypatch.setattr(bc, "_SEARCH_ROOTS", (str(tmp_path),))

        result = find_callers([str(module_a)])
        assert str(module_a) not in result

    def test_no_importers_returns_empty(self, tmp_path, monkeypatch):
        module_a = tmp_path / "module_a.py"
        module_a.write_text("def do_thing(): pass\n")

        import scripts.build_context as bc
        monkeypatch.setattr(bc, "_SEARCH_ROOTS", (str(tmp_path),))

        result = find_callers([str(module_a)])
        assert result == {}


# ---------------------------------------------------------------------------
# context_type routing
# ---------------------------------------------------------------------------

class TestContextType:
    def test_dashboard_path_gives_ui(self):
        assert context_type(["src/dashboard/app.py"]) == "ui"

    def test_domain_path_gives_backend(self):
        assert context_type(["src/domain/models.py"]) == "backend"

    def test_scripts_path_gives_backend(self):
        assert context_type(["scripts/generate_tests.py"]) == "backend"

    def test_mixed_gives_both(self):
        assert context_type(["src/dashboard/app.py", "src/domain/models.py"]) == "both"

    def test_empty_gives_backend(self):
        assert context_type([]) == "backend"


# ---------------------------------------------------------------------------
# build — end-to-end with mocked git
# ---------------------------------------------------------------------------

class TestBuild:
    def test_empty_diff_produces_valid_empty_context(self):
        with patch("scripts.build_context._run_git") as mock_git:
            mock_git.side_effect = subprocess.CalledProcessError(128, "git diff")
            result = build("HEAD~1", "HEAD")

        assert result["changed_files"] == []
        assert result["changed_symbols"] == {}
        assert result["callers"] == {}
        assert result["context_type"] == "backend"
        assert result["diff_excerpts"] == {}

    def test_result_has_all_required_keys(self):
        with patch("scripts.build_context._run_git", return_value=""):
            result = build("HEAD~1", "HEAD")

        assert set(result.keys()) == {
            "changed_files",
            "changed_symbols",
            "symbol_signatures",
            "callers",
            "context_type",
            "diff_excerpts",
            "file_contents",
            "file_imports",
            "file_directives",
            "existing_tests",
        }
