# Research: httpx

**Version:** httpx==0.28.1
**PyPI:** verified exists
**Status:** Current

## Correct Approach

```python
import httpx

# Synchronous
with httpx.Client(timeout=30.0) as client:
    resp = client.get("https://example.com/api")
    resp.raise_for_status()
    data = resp.json()

# Async
async with httpx.AsyncClient(timeout=30.0) as client:
    resp = await client.get("https://example.com/api")
```

## What We Ruled Out

| Approach | Why Rejected |
|----------|--------------|
| `requests` library | Sync-only; httpx covers both sync and async, and is already required by `anthropic` |
| `aiohttp` directly | Extra dependency; httpx AsyncClient covers the same use case |
| `httpx.get(url)` top-level convenience | Creates a new connection per call; prefer a Client context manager for connection reuse |

## Security Assessment

- [x] CVE check: CVE-2021-41945 (SSRF via malformed URLs) — fixed in 0.23.0, well below current pinned minimum of 0.27.0. No known CVEs against 0.27.x or 0.28.x. Safety DB reports 1 historical vulnerability (the 2021 SSRF), no active advisories.
- [x] Maintenance: Last release 2024-12-06. Actively maintained by Encode (Tom Christie). Regular releases.
- [x] License: BSD-3-Clause — compatible with project.
- [x] Transitive deps: 4 required (anyio, certifi, httpcore, idna). httpcore is the only non-stdlib dep not shared with the rest of the stack. Sniffio is pulled in via anyio. No known issues.

## Known Gotchas

- `httpx` does not follow redirects by default for non-GET methods (unlike `requests`); set `follow_redirects=True` explicitly.
- `httpx.Client` is not thread-safe for concurrent requests from multiple threads — use separate client instances per thread or use `AsyncClient`.
- `timeout` defaults changed in 0.20: the default is now 5s total. Set an explicit `timeout` for long-running API calls.
- HTTP/2 support requires the `httpx[http2]` extra (`h2` package).
