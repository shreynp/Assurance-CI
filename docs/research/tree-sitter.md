# Research: tree-sitter

**Version:** tree-sitter==0.25.2
**PyPI:** verified exists
**Status:** Current

## Correct Approach

```python
import tree_sitter_typescript as ts_typescript
from tree_sitter import Language, Parser

# Build the TypeScript language (tree-sitter >= 0.21 API)
TS_LANGUAGE = Language(ts_typescript.language_typescript())
parser = Parser(TS_LANGUAGE)

code = b"""
function greet(name: string): string {
  return `Hello, ${name}`;
}
"""

tree = parser.parse(code)
root = tree.root_node
print(root.type)  # "program"

# Walk the AST
def walk(node, indent=0):
    print(" " * indent + node.type)
    for child in node.children:
        walk(child, indent + 2)

walk(root)
```

## What We Ruled Out

| Approach | Why Rejected |
|----------|--------------|
| `ast` module (Python stdlib) | Python-only; cannot parse TypeScript |
| `esprima-python` | JavaScript-only; stale (last release 2019) |
| Regex-based TypeScript parsing | Brittle; cannot handle nested scopes or JSX |
| `libcst` | Python-only CST parser |

## Security Assessment

- [x] CVE check: CVE-2026-25727 — stack exhaustion DoS in tree-sitter core when parsing deeply-nested or adversarial input. Affects the core library. Mitigate by not parsing untrusted code with unbounded recursion depth, or setting a parse timeout. Monitor for a patched release.
- [x] Maintenance: Last release 2025-09-25 (v0.25.2). Project is maintained by Max Brunsfeld (GitHub: tree-sitter org). Linux Foundation Security Insights tracked. Active development, though releases are less frequent than 2023-2024.
- [x] License: MIT — compatible with project.
- [x] Transitive deps: 0 required at runtime. Test extras pull in language grammar packages. Pure Python wrapper with a C extension.

> **NOTE: Effectively single-maintainer.** Max Brunsfeld leads development. The tree-sitter org has grown community contributors, but the core Python bindings are primarily his work. Linux Foundation involvement provides some governance backstop.

## Known Gotchas

- **API changed significantly in 0.22.x**: `Language.build_library()` is removed. Use `Language(ts_typescript.language_typescript())` directly (as shown above). The old `Language.build_library("build/my-languages.so", [...])` pattern does not work in 0.21+.
- `tree-sitter>=0.21` requires the corresponding language grammar package (e.g., `tree-sitter-typescript`) to match the same major/minor series. Mixing `tree-sitter==0.25` with `tree-sitter-typescript==0.21` may cause ABI mismatches.
- The `Parser` object is not thread-safe; create one per thread.
- `node.text` returns `bytes`, not `str`. Decode with `.decode("utf-8")`.
- Parse errors produce `ERROR` nodes rather than raising exceptions — always check `tree.root_node.has_error` after parsing untrusted input.
