"""Incremental context builder for AI test generation.

Produces context.json describing what changed in a commit: changed files,
changed symbols (AST-level), and first-level callers in src/ and scripts/.

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


def changed_symbols(filepath: str, base: str, head: str) -> list[str]:
    """Return top-level names that appear in the diff for filepath."""
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


def diff_excerpt(filepath: str, base: str, head: str) -> str:
    """Return targeted diff lines for filepath."""
    try:
        return _run_git(["diff", base, head, "--", filepath])
    except subprocess.CalledProcessError:
        return ""


def find_callers(changed_paths: list[str]) -> dict[str, list[str]]:
    """Scan src/ and scripts/ for files that import any of the changed modules (1 level)."""
    changed_modules: set[str] = set()
    for p in changed_paths:
        path = Path(p)
        if path.suffix == ".py":
            # e.g. src/domain/models.py → src.domain.models and models
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


def context_type(changed_paths: list[str]) -> str:
    has_ui = any("dashboard" in p for p in changed_paths)
    has_backend = any("domain" in p or "scripts" in p for p in changed_paths)
    if has_ui and has_backend:
        return "both"
    if has_ui:
        return "ui"
    return "backend"


def build(base: str, head: str) -> dict:
    files = changed_files(base, head)
    py_files = [f for f in files if f.endswith(".py")]

    symbols: dict[str, list[str]] = {}
    excerpts: dict[str, str] = {}
    for f in py_files:
        syms = changed_symbols(f, base, head)
        if syms:
            symbols[f] = syms
        excerpt = diff_excerpt(f, base, head)
        if excerpt:
            excerpts[f] = excerpt

    return {
        "changed_files": files,
        "changed_symbols": symbols,
        "callers": find_callers(py_files),
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
