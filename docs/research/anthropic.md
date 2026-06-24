# Research: anthropic

**Version:** anthropic==0.112.0
**PyPI:** verified exists
**Status:** Current

## Correct Approach

```python
import anthropic

client = anthropic.Anthropic(api_key="...")  # reads ANTHROPIC_API_KEY env var by default

message = client.messages.create(
    model="claude-opus-4-5",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Hello"}],
)
print(message.content[0].text)
```

## What We Ruled Out

| Approach | Why Rejected |
|----------|--------------|
| `import anthropic; anthropic.Completion.create(...)` | Pre-v0.3 API — removed; use `client.messages.create()` |
| Passing `api_key` as positional arg | Not supported; use keyword arg or env var |
| `claude-v1`, `claude-instant-1` model names | Deprecated; use `claude-3-*` or `claude-opus-4-5` |

## Security Assessment

- [x] CVE check: No CVEs against the `anthropic` Python package itself. MCP-related CVEs (CVE-2026-30623, CVE-2025-49596) affect the MCP SDK transport layer, not the core messages API. Not applicable to this project's usage pattern.
- [x] Maintenance: Released 2026-06-24 (same day as this note). Active release cadence — multiple releases per month. Maintained by Anthropic, Inc.
- [x] License: MIT — compatible with project.
- [x] Transitive deps: 8 required (anyio, distro, docstring-parser, httpx, jiter, pydantic, sniffio, typing-extensions). Extras add boto3, aiohttp, mcp, google-auth. Core 8 are well-maintained. No known issues.

> **NOTE: Single-corporate maintainer.** All releases come from Anthropic's internal team. No independent community maintainers — API-breaking changes can ship without deprecation notice (as happened with the v0.3 and v0.5 message API reworks).

## Known Gotchas

- The `Anthropic()` constructor silently succeeds even without an API key set; the error only surfaces on the first API call.
- Streaming responses require `client.messages.stream(...)` context manager, not `.create(..., stream=True)`.
- `anthropic>=0.40` enforces `typing-extensions>=4.14` — pin if building a slim container.
- Token counting changed between 0.9x and 0.10x: `input_tokens` on the response now always reflects the post-cache value; use `cache_read_input_tokens` for billing.
