# Research: playwright

**Version:** playwright==1.60.0
**PyPI:** verified exists
**Status:** Current

## Correct Approach

```python
from playwright.sync_api import sync_playwright, expect

def test_page_title():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto("https://example.com")
        expect(page).to_have_title("Example Domain")
        browser.close()

# In pytest context, use the `page` fixture from pytest-playwright instead:
def test_with_fixture(page):
    page.goto("https://example.com")
    expect(page).to_have_title("Example Domain")
```

After install: `playwright install` (downloads browser binaries).

## What We Ruled Out

| Approach | Why Rejected |
|----------|--------------|
| `selenium` | Requires external WebDriver; slower; less reliable auto-waiting |
| `pyppeteer` | Unmaintained Chrome-only wrapper; Playwright covers Chromium, Firefox, WebKit |
| `requests-html` | No JavaScript execution; unsuitable for SPA testing |

## Security Assessment

- [x] CVE check: CVE-2025-59288 — installer curl script used `-k` (skip SSL verification), fixed in 1.55.1. Current version 1.60.0 is patched. Indirect OpenSSL CVEs (CVE-2024-5535, CVE-2025-15467, CVE-2026-28387) exist via embedded Chromium — mitigate by keeping playwright updated and running in isolated CI environments.
- [x] Maintenance: Released 2026-05-18. Microsoft-maintained. Very active — monthly releases tracking browser versions.
- [x] License: Apache-2.0 (confirmed from maintainer field `Microsoft Corporation License-Expression: Apache-2.0`) — compatible with project.
- [x] Transitive deps: 2 direct (pyee, greenlet). However, browser binaries (~300MB per browser) are downloaded separately via `playwright install` and are not tracked by pip's dependency graph. Chromium binary bundles OpenSSL — see CVE note above.

> **NOTE:** Playwright downloads browser binaries that are not managed by pip. These binaries contain bundled OpenSSL/libssl with their own CVE surface. Run `playwright install --with-deps chromium` in CI; pin the playwright version to control which Chromium build is used.

## Known Gotchas

- `playwright install` must be run after every version upgrade — the Python package version gates which browser version is downloaded.
- `sync_playwright()` is not thread-safe; use `async_playwright()` for parallel tests or use `pytest-playwright`'s built-in browser fixture which handles isolation.
- `expect()` assertions use built-in auto-retry (up to 5s by default); don't wrap them in `time.sleep()` calls.
- Network interception (`page.route()`) must be set up before the navigation that triggers the request.
- The `page` fixture from `pytest-playwright` creates a new page per test by default; use `browser_context` fixture for session sharing.
