# Research: pytest-cov

**Version:** pytest-cov==7.1.0
**PyPI:** verified exists
**Status:** Current

## Correct Approach

```toml
# pyproject.toml
[tool.pytest.ini_options]
addopts = "--cov=src --cov-report=term-missing --cov-report=xml:coverage.xml --cov-fail-under=80"

[tool.coverage.run]
source = ["src"]
omit = ["tests/*", "**/__init__.py"]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "if TYPE_CHECKING:",
    "raise NotImplementedError",
]
```

```bash
# Run with coverage
pytest --cov=src --cov-report=html tests/
```

## What We Ruled Out

| Approach | Why Rejected |
|----------|--------------|
| `coverage run -m pytest` | Extra step; pytest-cov integrates seamlessly as a plugin |
| Manual coverage thresholds in CI | `--cov-fail-under` provides a single source of truth |

## Security Assessment

- [x] CVE check: No known CVEs. Development tooling; not a runtime dependency.
- [x] Maintenance: Released 2026-03-21. Maintained by the pytest-dev org (Marc Schlaich and others). Active.
- [x] License: MIT — compatible with project.
- [x] Transitive deps: 3 required (coverage[toml], pluggy, pytest). `coverage[toml]>=7.10.6` is the actual measurement engine from Ned Batchelder — well-maintained.

## Known Gotchas

- `--cov-fail-under` counts combined branch + statement coverage only if `branch = true` is set in `[tool.coverage.run]`; otherwise it's statement-only.
- Running pytest-cov alongside `pytest-xdist` (parallel tests) requires `--cov-config` to be set and each worker to write to separate coverage files — use `pytest-xdist`'s `--dist loadfile` and enable `concurrency = multiprocessing` in coverage config.
- Branch coverage for `async` functions requires `coverage>=7.x` with `asyncio` concurrency enabled: `concurrency = asyncio`.
- HTML reports write to `htmlcov/` by default — add to `.gitignore`.
- In CI, use `--cov-report=xml` for integration with Codecov/Coveralls rather than the terminal report.
