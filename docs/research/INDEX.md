# Research Index

Library and API research notes. Each note includes: correct approach, ruled-out alternatives, and security assessment.

| Topic | File | Version | Status | Date |
|-------|------|---------|--------|------|
| anthropic | [anthropic.md](anthropic.md) | anthropic==0.112.0 | Current | 2026-06-24 |
| httpx | [httpx.md](httpx.md) | httpx==0.28.1 | Current | 2026-06-24 |
| pytest | [pytest.md](pytest.md) | pytest==9.1.1 | Current | 2026-06-24 |
| pytest-bdd | [pytest-bdd.md](pytest-bdd.md) | pytest-bdd==8.1.0 | Current | 2026-06-24 |
| playwright | [playwright.md](playwright.md) | playwright==1.60.0 | Current | 2026-06-24 |
| pytest-playwright | [pytest-playwright.md](pytest-playwright.md) | pytest-playwright==0.8.0 | Current | 2026-06-24 |
| python-dotenv | [python-dotenv.md](python-dotenv.md) | python-dotenv==1.2.2 | Current | 2026-06-24 |
| pydantic | [pydantic.md](pydantic.md) | pydantic==2.13.4 | Current | 2026-06-24 |
| tree-sitter | [tree-sitter.md](tree-sitter.md) | tree-sitter==0.25.2 | Current | 2026-06-24 |
| tree-sitter-typescript | [tree-sitter-typescript.md](tree-sitter-typescript.md) | tree-sitter-typescript==0.23.2 | Needs update | 2026-06-24 |
| pytest-asyncio | [pytest-asyncio.md](pytest-asyncio.md) | pytest-asyncio==1.4.0 | Current | 2026-06-24 |
| pytest-cov | [pytest-cov.md](pytest-cov.md) | pytest-cov==7.1.0 | Current | 2026-06-24 |
| ruff | [ruff.md](ruff.md) | ruff==0.15.19 | Current | 2026-06-24 |

## Flags

- **Single-maintainer packages**: `python-dotenv` (Saurabh Kumar), `pytest-bdd` (Alessio Bogon), `tree-sitter` / `tree-sitter-typescript` (Max Brunsfeld)
- **Packages with >20 transitive deps**: none in this stack
- **Version mismatch**: `tree-sitter==0.25.2` vs `tree-sitter-typescript==0.23.2` — grammar package lags the core by two minors; monitor for 0.25.x-compatible release
- **Active CVEs to watch**: CVE-2026-25727 (tree-sitter stack exhaustion DoS); Playwright OpenSSL indirect CVEs (CVE-2024-5535, CVE-2025-15467, CVE-2026-28387)

## Template Location
Copy from `.claude/agents/research-assistant.md` for format.

## Usage
Before integrating any new library:
1. Check this index for an existing note
2. If none exists, spawn the `research-assistant` agent to produce one
3. Add the entry to this index once the note is written
