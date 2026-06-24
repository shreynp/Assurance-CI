# Research: pytest-bdd

**Version:** pytest-bdd==8.1.0
**PyPI:** verified exists
**Status:** Current

## Correct Approach

```gherkin
# features/login.feature
Feature: User login
  Scenario: Successful login
    Given the user is on the login page
    When they enter valid credentials
    Then they should be redirected to the dashboard
```

```python
# tests/test_login.py
from pytest_bdd import given, when, then, scenario

@scenario("../features/login.feature", "Successful login")
def test_login():
    pass

@given("the user is on the login page")
def login_page(page):  # page fixture from pytest-playwright
    page.goto("/login")

@when("they enter valid credentials")
def enter_credentials(page):
    page.fill("#email", "user@example.com")
    page.fill("#password", "secret")
    page.click("button[type=submit]")

@then("they should be redirected to the dashboard")
def check_redirect(page):
    assert "/dashboard" in page.url
```

## What We Ruled Out

| Approach | Why Rejected |
|----------|--------------|
| `behave` | Not pytest-native; can't use pytest fixtures directly |
| `pytest-cucumber` | Low adoption, less maintained |
| Raw pytest parametrize for BDD-style tests | Loses Gherkin traceability required by project SPEC |

## Security Assessment

- [x] CVE check: No known CVEs. Test framework, runs in controlled CI environment.
- [x] Maintenance: Released 2024-12-05. Maintained by Alessio Bogon (primary) with original author Oleg Pidsadnyi. Active GitHub repo under pytest-dev org.
- [x] License: MIT — compatible with project.
- [x] Transitive deps: 6 (Mako, gherkin-official, packaging, parse, parse-type, typing-extensions). `gherkin-official<30.0.0,>=29.0.0` pins tightly — watch for upstream gherkin spec bumps.

> **NOTE: Effectively single-maintainer.** Alessio Bogon drives most active development. If unavailable, the project would stall.

## Known Gotchas

- **Breaking change in 8.x**: `bdd_features_base_dir` is now relative to pytest root, not CWD. Update `conftest.py` if using this setting.
- **Breaking change in 8.x**: Tags can no longer have spaces (`@tag one` is invalid). Use `@tag_one`.
- **Breaking change in 8.x**: `Feature:` keyword is required in all `.feature` files.
- Step argument names `datatable` and `docstring` are reserved — do not use as parameter names in step functions.
- Multiline step text must use triple-quotes; bare indented text blocks are no longer valid.
- The `gherkin-official` dependency pins tightly (`<30.0.0,>=29.0.0`); a gherkin-official 30.x release would break installation.
