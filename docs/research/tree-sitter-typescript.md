# Research: tree-sitter-typescript

**Version:** tree-sitter-typescript==0.23.2
**PyPI:** verified exists
**Status:** Needs update

## Correct Approach

```python
import tree_sitter_typescript as ts_typescript
from tree_sitter import Language, Parser

# TypeScript parser
ts_lang = Language(ts_typescript.language_typescript())
ts_parser = Parser(ts_lang)

# TSX parser (for React .tsx files)
tsx_lang = Language(ts_typescript.language_tsx())
tsx_parser = Parser(tsx_lang)

code = b"const x: number = 42;"
tree = ts_parser.parse(code)
```

## What We Ruled Out

| Approach | Why Rejected |
|----------|--------------|
| Building grammar from source via `tree-sitter generate` | Requires `node` + `tree-sitter-cli`; PyPI package ships prebuilt binaries |
| `tree-sitter-javascript` alone | Does not understand TypeScript type annotations |

## Security Assessment

- [x] CVE check: No CVEs specific to `tree-sitter-typescript`. The broader tree-sitter ecosystem had CVE-2026-25727 (stack exhaustion in core); see `tree-sitter.md`.
- [x] Maintenance: Last PyPI release 2024-11-11 (v0.23.2). The upstream grammar repo (github.com/tree-sitter/tree-sitter-typescript) is actively maintained with more recent commits. PyPI packaging may lag behind. Authors: Max Brunsfeld and Amaan Qureshi.
- [x] License: MIT — compatible with project.
- [x] Transitive deps: 1 optional (`tree-sitter~=0.23` for the `core` extra). At runtime, depends on `tree-sitter` being installed separately.

> **NOTE: Version mismatch warning.** The project installs `tree-sitter>=0.21.0` (latest: 0.25.2) but `tree-sitter-typescript>=0.21.0` (latest: 0.23.2). The two packages use different minor versions. The `tree-sitter-typescript` 0.23.x grammar was built against tree-sitter 0.23.x ABI. Running it against tree-sitter 0.25.x may work (the Python binding is version-tolerant) but is untested. Consider pinning both to compatible versions: `tree-sitter==0.23.x` and `tree-sitter-typescript==0.23.2`, or upgrading tree-sitter-typescript if a 0.25.x-compatible release is available.

> **NOTE: Effectively single-maintainer.** Same maintainer as `tree-sitter` core.

## Known Gotchas

- Provides two parsers: `language_typescript()` for `.ts` files and `language_tsx()` for `.tsx` files. They are separate; do not use the TypeScript parser on `.tsx` files.
- Grammar changes between minor versions can alter node types and field names — code walking the AST must be tested after upgrades.
- `node.text` returns `bytes`; decode to `str` before comparison.
- The `tree-sitter~=0.23` constraint in the `core` extra means this package's own test suite is pinned to 0.23. Production usage with 0.25.x is an unsupported configuration until a new release ships.
