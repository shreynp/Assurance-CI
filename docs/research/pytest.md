# Research: pytest

**Version:** pytest==9.1.1
**PyPI:** verified exists
**Status:** Current

## Correct Approach

```python
# conftest.py
import pytest

@pytest.fixture
def my_fixture():
    return {"key": "value"}

# test_example.py
def test_something(my_fixture):
    assert my_fixture["key"] == "value"
```

Run with: `pytest tests/ -v --tb=short`

## What We Ruled Out

| Approach | Why Rejected |
|----------|--------------|
| `unittest` directly | No fixtures, no parametrize, incompatible with pytest-bdd step injection |
| `nose` / `nose2` | Unmaintained; pytest is the de-facto standard |
| `pytest<8` | pyproject.toml requires `>=8.0.0`; 8.x has improved assertion rewriting |

## Security Assessment

- [x] CVE check: No known CVEs against pytest itself. Framework runs test code in a trusted environment by design.
- [x] Maintenance: Released 2026-06-19. Actively maintained by the pytest-dev team (7 named maintainers including Brianna Laugher, Holger Krekel, Ronny Pfannschmidt). Well-funded OSS project.
- [x] License: MIT (confirmed via OSI classifier) — compatible with project.
- [x] Transitive deps: 5 required runtime deps (iniconfig, packaging, pluggy, pygments, colorama-win32). All mature and stable. 14 total entries in requires_dist including extras.

## Known Gotchas

- pytest 9.x dropped support for Python 3.8 and 3.9. Project requires Python >=3.11, so no issue.
- `--import-mode=importlib` (new default candidate in 9.x) can change how test modules are discovered — check if `conftest.py` imports break.
- `pytest.ini_options` in `pyproject.toml` is the preferred config location (as used in this project). Avoid mixing with `setup.cfg`.
- `pluggy<2` constraint means the plugin system has a hard cap; third-party plugins must be compatible.
