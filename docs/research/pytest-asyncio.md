# Research: pytest-asyncio

**Version:** pytest-asyncio==1.4.0
**PyPI:** verified exists
**Status:** Current

## Correct Approach

```python
# pyproject.toml — required configuration
# [tool.pytest.ini_options]
# asyncio_mode = "auto"   # or "strict" (now the default in 1.4.0)

# test_async.py
import pytest
import asyncio

# With asyncio_mode = "auto": no decorator needed
async def test_async_operation():
    await asyncio.sleep(0)
    assert True

# With asyncio_mode = "strict" (default in 1.4.0): explicit marker required
@pytest.mark.asyncio
async def test_async_explicit():
    await asyncio.sleep(0)
    assert True

# Async fixture
@pytest.fixture
async def async_client():
    async with httpx.AsyncClient() as client:
        yield client
```

## What We Ruled Out

| Approach | Why Rejected |
|----------|--------------|
| `asyncio.run()` inside sync test | Cannot use async fixtures; creates a new event loop per call |
| `pytest-trio` | Trio-specific; project uses asyncio |
| `anyio` pytest plugin | More complex; pytest-asyncio is the standard for asyncio-only projects |

## Security Assessment

- [x] CVE check: No known CVEs. Test infrastructure only; not exposed to untrusted input at runtime.
- [x] Maintenance: Released 2026-05-26. Maintained by the pytest-dev team. Active development.
- [x] License: Apache-2.0 — compatible with project.
- [x] Transitive deps: 3 required (pytest>=8.4, typing-extensions for Python<3.13, backports-asyncio-runner for Python<3.11). Project requires Python>=3.11, so `backports-asyncio-runner` will not be installed.

## Known Gotchas

- **Breaking change in 1.4.0**: Default `asyncio_mode` is now `strict`. Without explicit configuration, async tests without `@pytest.mark.asyncio` will be silently skipped or raise a warning. Add `asyncio_mode = "auto"` to `pyproject.toml` if you want implicit marking.
- **Breaking change from 0.x**: `legacy` mode removed in 1.0.0. If upgrading from 0.19.x, ensure no `asyncio_mode = "legacy"` is set.
- **Breaking change in 1.4.0**: Requires `pytest>=8.4` (stricter than the project's `>=8.0.0` floor). Ensure pytest is upgraded.
- The `@pytest_asyncio.fixture` decorator is required for async fixtures in strict mode (not just `@pytest.fixture`).
- Event loop scope: by default, a new event loop is created per test. For shared state (e.g., a DB connection), configure `@pytest.fixture(loop_scope="session")`.
- pyproject.toml note: this dep is listed as dev-only and currently unused by the project's sync tests. Enable when async tests are introduced.
