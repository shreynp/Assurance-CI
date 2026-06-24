# Research: ruff

**Version:** ruff==0.15.19
**PyPI:** verified exists
**Status:** Current

## Correct Approach

```toml
# pyproject.toml (already configured in this project)
[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I"]  # pycodestyle errors, pyflakes, isort
ignore = ["E501"]          # line-too-long (handled by line-length)
```

```bash
# Lint
ruff check src/ tests/

# Auto-fix
ruff check --fix src/ tests/

# Format (replaces black)
ruff format src/ tests/

# Check formatting without writing
ruff format --check src/ tests/
```

## What We Ruled Out

| Approach | Why Rejected |
|----------|--------------|
| `flake8` + `isort` + `black` | Three separate tools; ruff replaces all three at 10-100x speed |
| `pylint` | Slower; more opinionated; harder to suppress selectively |
| `mypy` alone | Type checking only; ruff handles linting and formatting |

## Security Assessment

- [x] CVE check: No known CVEs. Dev-only linting tool; zero attack surface at runtime.
- [x] Maintenance: Released 2026-06-24 (same day as this note — very active). Maintained by Astral (formerly Astral-sh), a well-funded company. Charlie Marsh leads development.
- [x] License: MIT — compatible with project.
- [x] Transitive deps: 0. Ruff ships as a single pre-compiled Rust binary with no Python dependencies. This is by design — zero install footprint beyond the binary itself.

## Known Gotchas

- Ruff's rule set evolves rapidly — rule codes added in newer versions may trigger lint failures if `select = ["ALL"]` is used. The project's conservative `["E", "F", "I"]` selection avoids this.
- `ruff format` is not 100% identical to `black` output in edge cases involving trailing commas and magic trailing comma handling. If migrating from black, do a one-time format pass and commit before enabling in CI.
- `ruff check --fix` can make semantic changes when using fixable rules (e.g., `UP` for pyupgrade). Review auto-fixes before committing.
- `target-version = "py312"` in pyproject.toml means ruff may flag constructs valid in 3.11 but not recommended in 3.12. The project requires Python >=3.11 — consider aligning to `py311`.
- Pre-commit hook: use `ruff check --force-exclude` to respect per-directory `exclude` settings.
