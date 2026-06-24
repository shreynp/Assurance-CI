"""Incremental context builder for AI test generation.

Produces context.json describing what changed in a commit: changed files,
changed symbols (AST-level), callers, and diff excerpts — for both Python
and TypeScript/TSX/JavaScript/JSX files.

CLI: python scripts/build_context.py --base HEAD~1 --head HEAD --output context.json
"""
from __future__ import annotations

import argparse
import ast
import json
import subprocess
import sys
from pathlib import Path

_SEARCH_ROOTS = ("src", "scripts")
_JS_TS_EXTS = {".ts", ".tsx", ".js", ".jsx"}


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------

def _run_git(args: list[str]) -> str:
    result = subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise subprocess.CalledProcessError(result.returncode, ["git", *args], result.stdout, result.stderr)
    return result.stdout


def changed_files(base: str, head: str) -> list[str]:
    try:
        out = _run_git(["diff", "--name-only", base, head])
    except subprocess.CalledProcessError:
        return []
    return [f for f in out.splitlines() if f]


def diff_excerpt(filepath: str, base: str, head: str) -> str:
    try:
        return _run_git(["diff", base, head, "--", filepath])
    except subprocess.CalledProcessError:
        return ""


# ---------------------------------------------------------------------------
# Python AST — changed symbols + callers
# ---------------------------------------------------------------------------

def changed_symbols(filepath: str, base: str, head: str) -> list[str]:
    """Return top-level names that appear in the diff for a Python file."""
    try:
        diff_text = _run_git(["diff", base, head, "--", filepath])
    except subprocess.CalledProcessError:
        return []

    path = Path(filepath)
    if not path.exists() or path.suffix != ".py":
        return []

    try:
        tree = ast.parse(path.read_text())
    except SyntaxError:
        return []

    top_level_names = {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        and isinstance(getattr(node, "col_offset", 1), int)
        and node.col_offset == 0
    }

    added_lines = {
        line[1:]
        for line in diff_text.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    }
    return [name for name in top_level_names if any(name in line for line in added_lines)]


def find_py_callers(changed_paths: list[str]) -> dict[str, list[str]]:
    """Scan src/ and scripts/ for Python files that import any of the changed modules (1 level)."""
    changed_modules: set[str] = set()
    for p in changed_paths:
        path = Path(p)
        if path.suffix == ".py":
            parts = path.with_suffix("").parts
            changed_modules.add(".".join(parts))
            changed_modules.add(path.stem)

    callers: dict[str, list[str]] = {}
    for root in _SEARCH_ROOTS:
        root_path = Path(root)
        if not root_path.exists():
            continue
        for py_file in root_path.rglob("*.py"):
            str_path = str(py_file)
            if str_path in changed_paths:
                continue
            try:
                tree = ast.parse(py_file.read_text())
            except SyntaxError:
                continue

            imported: list[str] = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name in changed_modules:
                            imported.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    if module in changed_modules:
                        imported.extend(alias.name for alias in node.names)

            if imported:
                callers[str_path] = imported

    return callers


# ---------------------------------------------------------------------------
# TypeScript/TSX/JS/JSX AST — changed symbols + callers
# ---------------------------------------------------------------------------

def _ts_parser(filepath: str):
    """Return a tree-sitter Parser for the given file extension, or None if unavailable."""
    ext = Path(filepath).suffix.lower()
    if ext not in _JS_TS_EXTS:
        return None
    try:
        from tree_sitter import Language, Parser
        import tree_sitter_typescript as _tsmod
        lang = Language(_tsmod.language_tsx() if ext in (".tsx", ".jsx") else _tsmod.language_typescript())
        return Parser(lang)
    except Exception:
        return None


def _ts_decl_name(node) -> str | None:
    """Extract the primary identifier from a top-level TS/TSX declaration node."""
    t = node.type

    if t in (
        "function_declaration", "generator_function_declaration",
        "class_declaration", "abstract_class_declaration",
        "interface_declaration", "type_alias_declaration", "enum_declaration",
    ):
        for child in node.children:
            if child.type in ("identifier", "type_identifier"):
                return child.text.decode()

    if t == "lexical_declaration":
        for child in node.children:
            if child.type == "variable_declarator":
                for sub in child.children:
                    if sub.type == "identifier":
                        return sub.text.decode()

    if t == "export_statement":
        for child in node.children:
            name = _ts_decl_name(child)
            if name:
                return name
            # export default Identifier
            if child.type == "identifier":
                return child.text.decode()

    return None


def changed_symbols_ts(filepath: str, base: str, head: str) -> list[str]:
    """Return top-level names that appear in the diff for a TS/TSX/JS/JSX file."""
    try:
        diff_text = _run_git(["diff", base, head, "--", filepath])
    except subprocess.CalledProcessError:
        return []

    path = Path(filepath)
    if not path.exists():
        return []

    parser = _ts_parser(filepath)
    if parser is None:
        return []

    try:
        tree = parser.parse(path.read_bytes())
    except Exception:
        return []

    added_lines = {
        line[1:]
        for line in diff_text.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    }

    names = []
    for node in tree.root_node.children:
        name = _ts_decl_name(node)
        if name and any(name in line for line in added_lines):
            names.append(name)
    return names


def find_ts_callers(changed_paths: list[str]) -> dict[str, list[str]]:
    """Scan src/ for TS/TSX/JS/JSX files that import any of the changed modules (1 level).

    Matches by file stem (e.g. 'completeness-ring') against the import specifier path,
    since TS imports use relative paths rather than module names.
    """
    changed_stems = {Path(p).stem for p in changed_paths if Path(p).suffix in _JS_TS_EXTS}
    if not changed_stems:
        return {}

    callers: dict[str, list[str]] = {}
    for root in _SEARCH_ROOTS:
        root_path = Path(root)
        if not root_path.exists():
            continue
        for ts_file in root_path.rglob("*"):
            if ts_file.suffix not in _JS_TS_EXTS:
                continue
            str_path = str(ts_file)
            if str_path in changed_paths:
                continue

            parser = _ts_parser(str_path)
            imported: list[str] = []

            if parser is not None:
                try:
                    tree = parser.parse(ts_file.read_bytes())
                    for node in tree.root_node.children:
                        if node.type != "import_statement":
                            continue
                        for child in node.children:
                            if child.type == "string":
                                specifier = child.text.decode().strip("'\"")
                                stem = Path(specifier).stem
                                if stem in changed_stems:
                                    imported.append(stem)
                except Exception:
                    pass
            else:
                # Graceful fallback: text scan for import paths
                try:
                    text = ts_file.read_text()
                    for stem in changed_stems:
                        if f"/{stem}'" in text or f'/{stem}"' in text or f"'{stem}'" in text or f'"{stem}"' in text:
                            imported.append(stem)
                except Exception:
                    pass

            if imported:
                callers[str_path] = imported

    return callers


# ---------------------------------------------------------------------------
# Context type classifier + top-level build
# ---------------------------------------------------------------------------

def context_type(changed_paths: list[str]) -> str:
    has_ui = any("dashboard" in p or "components" in p or "app" in p for p in changed_paths)
    has_backend = any("domain" in p or "scripts" in p or "api" in p or "lib" in p for p in changed_paths)
    if has_ui and has_backend:
        return "both"
    if has_ui:
        return "ui"
    return "backend"


def build(base: str, head: str) -> dict:
    files = changed_files(base, head)
    py_files = [f for f in files if f.endswith(".py")]
    ts_files = [f for f in files if Path(f).suffix in _JS_TS_EXTS]

    symbols: dict[str, list[str]] = {}
    excerpts: dict[str, str] = {}

    for f in py_files:
        syms = changed_symbols(f, base, head)
        if syms:
            symbols[f] = syms
        excerpt = diff_excerpt(f, base, head)
        if excerpt:
            excerpts[f] = excerpt

    for f in ts_files:
        syms = changed_symbols_ts(f, base, head)
        if syms:
            symbols[f] = syms
        excerpt = diff_excerpt(f, base, head)
        if excerpt:
            excerpts[f] = excerpt

    callers = {**find_py_callers(py_files), **find_ts_callers(ts_files)}

    return {
        "changed_files": files,
        "changed_symbols": symbols,
        "callers": callers,
        "context_type": context_type(files),
        "diff_excerpts": excerpts,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build incremental context for AI test generation")
    parser.add_argument("--base", default="HEAD~1", help="Base git ref")
    parser.add_argument("--head", default="HEAD", help="Head git ref")
    parser.add_argument("--output", default="context.json", help="Output JSON path")
    args = parser.parse_args()

    ctx = build(args.base, args.head)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(ctx, indent=2))
    print(f"context.json written to {out_path} ({len(ctx['changed_files'])} changed files)")


if __name__ == "__main__":
    main()
