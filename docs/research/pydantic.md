# Research: pydantic

**Version:** pydantic==2.13.4
**PyPI:** verified exists
**Status:** Current

## Correct Approach

```python
from pydantic import BaseModel, Field
from typing import Optional

class AssessmentResult(BaseModel):
    story_id: str
    score: float = Field(ge=0.0, le=1.0)
    passed: bool
    details: Optional[str] = None

# Validation
result = AssessmentResult(story_id="PROT-101", score=0.85, passed=True)
print(result.model_dump())  # NOT .dict() — that's Pydantic v1

# From dict
result2 = AssessmentResult.model_validate({"story_id": "PROT-102", "score": 0.5, "passed": False})
```

## What We Ruled Out

| Approach | Why Rejected |
|----------|--------------|
| `dataclasses` + manual validation | Already in use for current phase; pydantic reserved for Phase 1 schema validation per pyproject.toml comment |
| Pydantic v1 API (`.dict()`, `.parse_obj()`) | Removed in v2; use `.model_dump()`, `.model_validate()` |
| `attrs` + `cattrs` | Extra dependency; pydantic already required by `anthropic` |
| `marshmallow` | Separate serialization step; pydantic does both in one |

## Security Assessment

- [x] CVE check: CVE-2024-3772 — ReDoS via crafted email string in `EmailStr` validator; fixed in pydantic>=2.4.0. Current 2.13.4 is patched. CVE-2026-25580 and CVE-2026-25904 affect `pydantic-ai` (a separate package), not `pydantic` itself.
- [x] Maintenance: Released 2026-05-06. Maintained by Samuel Colvin and the Pydantic team at Pydantic Services Inc. Active, well-funded project.
- [x] License: MIT — compatible with project.
- [x] Transitive deps: 3 required (annotated-types, pydantic-core, typing-extensions). `pydantic-core` is a Rust-compiled extension — adds a native binary to the install. No known issues.

## Known Gotchas

- **Pydantic v2 is not backwards-compatible with v1.** `anthropic>=0.40` allows `pydantic>=1.9.0`, but if project code uses v2 APIs (`.model_dump()`, `model_validate()`), pin `pydantic>=2.0` explicitly.
- `pydantic-core` requires a compatible Rust ABI — must match the exact `pydantic` version that compiled it (the `==2.46.4` pin in pydantic 2.13.4's deps enforces this automatically).
- Model fields with `Optional[X]` are NOT automatically nullable in v2; use `Optional[X] = None` or `X | None = None`.
- `model_config = ConfigDict(strict=True)` enables strict type checking — no coercion (e.g., `"1"` does not become `1`).
- JSON schema generation changed significantly between v1 and v2; if generating OpenAPI schemas, verify output.
