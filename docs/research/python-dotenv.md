# Research: python-dotenv

**Version:** python-dotenv==1.2.2
**PyPI:** verified exists
**Status:** Current

## Correct Approach

```python
from dotenv import load_dotenv
import os

# Load .env file (call once at startup)
load_dotenv()  # looks for .env in CWD and parent dirs

api_key = os.getenv("ANTHROPIC_API_KEY")

# Or load from a specific path:
load_dotenv("/path/to/.env")

# Override existing env vars:
load_dotenv(override=True)
```

```ini
# .env
ANTHROPIC_API_KEY=sk-ant-...
BASE_URL=http://localhost:3000
```

## What We Ruled Out

| Approach | Why Rejected |
|----------|--------------|
| Hardcoding secrets in source | Never acceptable |
| `direnv` shell integration | Not portable across CI systems |
| `os.environ` manual export | Not committed-safe; fragile in CI |

## Security Assessment

- [x] CVE check: No known CVEs. Minimal attack surface — reads and parses text files; no network access.
- [x] Maintenance: Released 2026-03-01. Maintained by Saurabh Kumar (single author). Stable, low-churn library.
- [x] License: BSD-3-Clause — compatible with project.
- [x] Transitive deps: 0 required. Optional `click>=5.0` for the CLI. Zero-dependency for library use.

> **NOTE: Single-maintainer package.** Saurabh Kumar is the sole author and maintainer. The library is feature-complete and low-churn, which mitigates the risk, but there is no succession plan.

## Known Gotchas

- `load_dotenv()` does NOT override environment variables already set in the shell by default. In CI (where variables are set by the runner), you may need `load_dotenv(override=True)` to test with `.env` values.
- `.env` files should be in `.gitignore`. This project's `.gitignore` must exclude `.env`.
- Multiline values require quoting: `MY_VAR="line1\nline2"`. Unquoted values with newlines are parsed as the first line only.
- `dotenv_values()` returns a dict without modifying `os.environ` — useful for testing or validation without side effects.
- UTF-8 BOM in `.env` files can cause parse errors on Windows; use UTF-8 without BOM.
