# Research: pytest-playwright

**Version:** pytest-playwright==0.8.0
**PyPI:** verified exists
**Status:** Current

## Correct Approach

```python
# conftest.py — configure base URL and browser options
import pytest

def pytest_configure(config):
    config.addinivalue_line("markers", "smoke: smoke tests")

# pytest.ini / pyproject.toml
# [tool.pytest.ini_options]
# base_url = "http://localhost:3000"

# test_example.py — use built-in fixtures
from playwright.sync_api import expect

def test_home(page, base_url):
    page.goto(base_url)
    expect(page).to_have_title("My App")

# For headed mode in CI:
# pytest --headed --browser chromium
```

## What We Ruled Out

| Approach | Why Rejected |
|----------|--------------|
| Managing `sync_playwright()` context manually in every test | Verbose; pytest-playwright fixtures handle browser lifecycle and isolation |
| `pytest-selenium` | Selenium-based; incompatible with Playwright browser instances |

## Security Assessment

- [x] CVE check: No known CVEs against pytest-playwright itself. Security surface is inherited from `playwright` package (see playwright.md).
- [x] Maintenance: Released 2026-05-18 (in sync with playwright 1.60.0). Maintained by Microsoft. Versioned in lockstep with the playwright package.
- [x] License: Apache-2.0 — compatible with project.
- [x] Transitive deps: 4 (playwright, pytest, pytest-base-url, python-slugify). All are in the project's own dependency set.

## Known Gotchas

- `pytest-playwright` version must be compatible with the installed `playwright` version. They release in sync — always upgrade both together.
- The `browser` fixture defaults to Chromium. Pass `--browser firefox` or `--browser webkit` at the CLI for cross-browser runs.
- `--tracing on` flag enables trace recording for each test; significantly increases disk usage in CI.
- `page` fixture scope is `function` by default; override with `@pytest.fixture(scope="session")` for shared sessions, but be careful with test isolation.
- `pytest-base-url` (transitive dep) provides the `base_url` fixture; configure via `--base-url` CLI flag or `base_url` in `pyproject.toml`.
