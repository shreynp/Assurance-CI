"""Incremental context builder for AI test generation.

Produces context.json describing what changed in a commit: changed files,
changed symbols (AST-level), symbol signatures, callers, diff excerpts,
full file contents (small files), inbound imports, file directives, and
existing test files.

CLI: python scripts/build_context.py --base HEAD~1 --head HEAD --output context.json [--story-id PROT-NNN]
"""
from __future__ import annotations

import argparse
import ast
import json
import subprocess
from pathlib import Path

# Python caller scan: package-oriented layout
_SEARCH_ROOTS = ("src", "scripts")

# TS/TSX caller scan: covers Next.js App Router + Pages Router + common layouts
_TS_SEARCH_ROOTS = (
    "src", "app", "components", "lib", "hooks",
    "stores", "types", "utils", "pages", "features",
)

_JS_TS_EXTS = {".ts", ".tsx", ".js", ".jsx"}
_FILE_CONTENT_LINE_LIMIT = 200  # include full content for files at or under this many lines

# Avoid recursing into parameter/argument nodes when hunting for function bodies
_NO_RECURSE_TS = {"formal_parameters", "arguments", "call_expression", "template_string"}


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
# Python AST — symbols, signatures, imports, callers
# ---------------------------------------------------------------------------

def _py_signature(node: ast.AST, source: str) -> str | None:
    """Extract the def/class signature line(s) from a Python AST node."""
    lines = source.splitlines()
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        start = node.lineno - 1
        body_start = node.body[0].lineno - 1
        sig_lines = [ln.strip() for ln in lines[start:body_start]]
        return " ".join(sig_lines).rstrip()
    if isinstance(node, ast.ClassDef):
        return lines[node.lineno - 1].strip()
    return None


def _extract_py_symbols(filepath: str, base: str, head: str) -> tuple[list[str], dict[str, str]]:
    """Return (names, {name: signature}) for top-level Python symbols touched by the diff."""
    try:
        diff_text = _run_git(["diff", base, head, "--", filepath])
    except subprocess.CalledProcessError:
        return [], {}

    path = Path(filepath)
    if not path.exists() or path.suffix != ".py":
        return [], {}

    try:
        source = path.read_text()
        tree = ast.parse(source)
    except SyntaxError:
        return [], {}

    top_level = [
        node for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        and getattr(node, "col_offset", 1) == 0
    ]

    added_lines = {
        line[1:]
        for line in diff_text.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    }

    names: list[str] = []
    sigs: dict[str, str] = {}
    for node in top_level:
        name = node.name
        if any(name in line for line in added_lines):
            names.append(name)
            sig = _py_signature(node, source)
            if sig:
                sigs[name] = sig

    return names, sigs


def changed_symbols(filepath: str, base: str, head: str) -> list[str]:
    """Return top-level names that appear in the diff for a Python file."""
    return _extract_py_symbols(filepath, base, head)[0]


def file_imports_py(filepath: str) -> list[str]:
    """Return import specifiers from a Python source file."""
    path = Path(filepath)
    if not path.exists():
        return []
    try:
        tree = ast.parse(path.read_text())
    except SyntaxError:
        return []
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
    return imports


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


# Backward-compatible alias used by tests and external callers
find_callers = find_py_callers


# ---------------------------------------------------------------------------
# TypeScript/TSX/JS/JSX AST — symbols, signatures, imports, callers, directives
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
            if child.type == "identifier":
                return child.text.decode()

    return None


def _ts_decl_signature(node) -> str | None:
    """Extract the signature text (excluding the function body) from a TS/TSX declaration node."""
    t = node.type
    text = node.text.decode()

    # Delegate export_statement to its inner declaration, prepend export keyword
    if t == "export_statement":
        child_types = {c.type for c in node.children}
        prefix = "export default " if "default" in child_types else "export "
        for child in node.children:
            if child.type not in ("export", "default", "identifier", "string", ";"):
                inner = _ts_decl_signature(child)
                if inner:
                    return inner if inner.startswith("export") else prefix + inner
        return text.splitlines()[0].strip()

    # For interfaces and type aliases, include the full body when compact
    if t in ("interface_declaration", "type_alias_declaration"):
        return text if len(text) <= 300 else text.splitlines()[0].strip()

    # Find the body node (statement_block / class_body / enum_body) and truncate there
    def _body_offset(n, base: int) -> int | None:
        for child in n.children:
            if child.type in {"statement_block", "class_body", "enum_body"}:
                return child.start_byte - base
            if child.type not in _NO_RECURSE_TS:
                deeper = _body_offset(child, base)
                if deeper is not None:
                    return deeper
        return None

    offset = _body_offset(node, node.start_byte)
    if offset is not None:
        sig = text[:offset].strip()
        if sig.endswith("=>"):
            sig = sig[:-2].strip()
        return sig or None

    # Fallback: truncate at first {
    idx = text.find("{")
    return text[:idx].strip() if idx > 0 else text[:300].strip()


def _ts_file_directives(filepath: str) -> list[str]:
    """Extract 'use client', 'use server', and similar React/Next.js directives from a TS/TSX file."""
    parser = _ts_parser(filepath)
    if parser is None:
        return []
    path = Path(filepath)
    if not path.exists():
        return []
    try:
        tree = parser.parse(path.read_bytes())
    except Exception:
        return []
    directives: list[str] = []
    for node in tree.root_node.children:
        # Directives appear as expression_statement > string at the very top
        if node.type == "expression_statement":
            for child in node.children:
                if child.type == "string":
                    val = child.text.decode().strip("'\"")
                    if val.startswith("use "):
                        directives.append(val)
        elif node.type == "string":
            val = node.text.decode().strip("'\"")
            if val.startswith("use "):
                directives.append(val)
        else:
            # Directives must precede all other statements
            break
    return directives


def _extract_ts_symbols(filepath: str, base: str, head: str) -> tuple[list[str], dict[str, str]]:
    """Return (names, {name: signature}) for TS/TSX symbols touched by the diff."""
    try:
        diff_text = _run_git(["diff", base, head, "--", filepath])
    except subprocess.CalledProcessError:
        return [], {}

    path = Path(filepath)
    if not path.exists():
        return [], {}

    parser = _ts_parser(filepath)
    if parser is None:
        return [], {}

    try:
        tree = parser.parse(path.read_bytes())
    except Exception:
        return [], {}

    added_lines = {
        line[1:]
        for line in diff_text.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    }

    names: list[str] = []
    sigs: dict[str, str] = {}
    for node in tree.root_node.children:
        name = _ts_decl_name(node)
        if name and any(name in line for line in added_lines):
            names.append(name)
            sig = _ts_decl_signature(node)
            if sig:
                sigs[name] = sig

    return names, sigs


def changed_symbols_ts(filepath: str, base: str, head: str) -> list[str]:
    """Return top-level names that appear in the diff for a TS/TSX/JS/JSX file."""
    return _extract_ts_symbols(filepath, base, head)[0]


def file_imports_ts(filepath: str) -> list[str]:
    """Return import specifiers from a TS/TSX/JS/JSX file."""
    parser = _ts_parser(filepath)
    if parser is None:
        return []
    path = Path(filepath)
    if not path.exists():
        return []
    try:
        tree = parser.parse(path.read_bytes())
    except Exception:
        return []
    imports: list[str] = []
    for node in tree.root_node.children:
        if node.type == "import_statement":
            for child in node.children:
                if child.type == "string":
                    imports.append(child.text.decode().strip("'\""))
    return imports


def find_ts_callers(changed_paths: list[str]) -> dict[str, list[str]]:
    """Scan Next.js source directories for TS/TSX/JS/JSX files that import any changed module (1 level).

    Matches by file stem against the import specifier path. Scans _TS_SEARCH_ROOTS which covers
    the standard Next.js App Router layout (app/, components/, lib/, hooks/, etc.) in addition to src/.
    """
    changed_stems = {Path(p).stem for p in changed_paths if Path(p).suffix in _JS_TS_EXTS}
    if not changed_stems:
        return {}

    callers: dict[str, list[str]] = {}
    for root in _TS_SEARCH_ROOTS:
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
# Full file contents (small files only)
# ---------------------------------------------------------------------------

def _file_contents(changed_paths: list[str]) -> dict[str, str]:
    """Return full text of changed files that are at or under _FILE_CONTENT_LINE_LIMIT lines."""
    contents: dict[str, str] = {}
    for p in changed_paths:
        path = Path(p)
        if not path.exists():
            continue
        try:
            text = path.read_text()
            if text.count("\n") <= _FILE_CONTENT_LINE_LIMIT:
                contents[p] = text
        except Exception:
            pass
    return contents


# ---------------------------------------------------------------------------
# File imports (inbound dependency list per changed file)
# ---------------------------------------------------------------------------

def _file_imports(filepath: str) -> list[str]:
    """Return import specifiers declared inside the given source file."""
    ext = Path(filepath).suffix.lower()
    if ext == ".py":
        return file_imports_py(filepath)
    if ext in _JS_TS_EXTS:
        return file_imports_ts(filepath)
    return []


# ---------------------------------------------------------------------------
# File directives ('use client' / 'use server' for Next.js)
# ---------------------------------------------------------------------------

def _collect_file_directives(changed_paths: list[str]) -> dict[str, list[str]]:
    """Return directives (e.g. 'use client') per changed TS/TSX file that declares one."""
    directives: dict[str, list[str]] = {}
    for p in changed_paths:
        if Path(p).suffix in _JS_TS_EXTS:
            found = _ts_file_directives(p)
            if found:
                directives[p] = found
    return directives


# ---------------------------------------------------------------------------
# Existing test file detection
# ---------------------------------------------------------------------------

def _find_existing_tests(changed_paths: list[str], story_id: str | None = None) -> dict[str, str]:
    """Find test files co-located with changed source files, plus previously generated tests."""
    existing: dict[str, str] = {}
    _ts_test_suffixes = (
        ".test.ts", ".test.tsx", ".spec.ts", ".spec.tsx",
        ".test.js", ".test.jsx", ".spec.js", ".spec.jsx",
    )

    for p in changed_paths:
        path = Path(p)
        stem = path.stem

        if path.suffix in _JS_TS_EXTS:
            # Co-located: same directory
            for suffix in _ts_test_suffixes:
                candidate = path.with_name(stem + suffix)
                if candidate.exists() and str(candidate) not in changed_paths:
                    try:
                        existing[str(candidate)] = candidate.read_text()
                    except Exception:
                        pass
            # Jest-style __tests__/ sibling directory
            tests_dir = path.parent / "__tests__"
            if tests_dir.exists():
                for suffix in _ts_test_suffixes:
                    candidate = tests_dir / (stem + suffix)
                    if candidate.exists() and str(candidate) not in changed_paths:
                        try:
                            existing[str(candidate)] = candidate.read_text()
                        except Exception:
                            pass

        if path.suffix == ".py":
            for candidate in (
                path.with_name(f"test_{stem}.py"),
                path.with_name(f"{stem}_test.py"),
                Path("tests") / f"test_{stem}.py",
            ):
                if candidate.exists() and str(candidate) not in changed_paths:
                    try:
                        existing[str(candidate)] = candidate.read_text()
                    except Exception:
                        pass

    # Previously generated tests for this story
    if story_id:
        story_dir = Path("generated") / story_id
        if story_dir.exists():
            for test_file in sorted(story_dir.rglob("*")):
                if test_file.is_file() and test_file.suffix in {".py", ".feature", ".ts", ".tsx"}:
                    try:
                        existing[str(test_file)] = test_file.read_text()
                    except Exception:
                        pass

    return existing


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


def build(base: str, head: str, story_id: str | None = None) -> dict:
    files = changed_files(base, head)
    py_files = [f for f in files if f.endswith(".py")]
    ts_files = [f for f in files if Path(f).suffix in _JS_TS_EXTS]
    all_source = py_files + ts_files

    symbols: dict[str, list[str]] = {}
    signatures: dict[str, dict[str, str]] = {}
    excerpts: dict[str, str] = {}

    for f in py_files:
        names, sigs = _extract_py_symbols(f, base, head)
        if names:
            symbols[f] = names
        if sigs:
            signatures[f] = sigs
        excerpt = diff_excerpt(f, base, head)
        if excerpt:
            excerpts[f] = excerpt

    for f in ts_files:
        names, sigs = _extract_ts_symbols(f, base, head)
        if names:
            symbols[f] = names
        if sigs:
            signatures[f] = sigs
        excerpt = diff_excerpt(f, base, head)
        if excerpt:
            excerpts[f] = excerpt

    callers = {**find_py_callers(py_files), **find_ts_callers(ts_files)}
    imports = {f: imps for f in all_source if (imps := _file_imports(f))}

    return {
        "changed_files": files,
        "changed_symbols": symbols,
        "symbol_signatures": signatures,
        "callers": callers,
        "context_type": context_type(files),
        "diff_excerpts": excerpts,
        "file_contents": _file_contents(all_source),
        "file_imports": imports,
        "file_directives": _collect_file_directives(ts_files),
        "existing_tests": _find_existing_tests(all_source, story_id),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build incremental context for AI test generation")
    parser.add_argument("--base", default="HEAD~1", help="Base git ref")
    parser.add_argument("--head", default="HEAD", help="Head git ref")
    parser.add_argument("--output", default="context.json", help="Output JSON path")
    parser.add_argument(
        "--story-id", default=None,
        help="Jira story ID (e.g. PROT-NNN) — used to include previously generated tests from generated/<story-id>/",
    )
    args = parser.parse_args()

    ctx = build(args.base, args.head, story_id=args.story_id)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(ctx, indent=2))
    print(f"context.json written to {out_path} ({len(ctx['changed_files'])} changed files)")


if __name__ == "__main__":
    main()
