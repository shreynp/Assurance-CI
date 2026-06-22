#!/usr/bin/env bash
# Assurance CI — smoke test script
# Run at session start. Fix any failures before starting new work.
set -e

echo "=== Assurance CI — Init Check ==="
PASS=0; WARN=0; FAIL=0

# 1. Environment check
if [ -f .env ]; then
  echo "✓ .env found"
  ((PASS++)) || true
else
  echo "⚠ .env not found — copy .env.example and set ANTHROPIC_API_KEY"
  ((WARN++)) || true
fi

# 2. Python virtual environment
if [ -d .venv ]; then
  # shellcheck source=/dev/null
  source .venv/bin/activate
  echo "✓ .venv activated"
  ((PASS++)) || true
else
  echo "✗ .venv not found"
  echo "  Fix: python -m venv .venv && source .venv/bin/activate && pip install -e '.[dev]'"
  ((FAIL++)) || true
fi

# 3. Core dependencies
if python -c "import anthropic, pytest, streamlit, playwright" 2>/dev/null; then
  echo "✓ Core dependencies available"
  ((PASS++)) || true
else
  echo "✗ Missing dependencies"
  echo "  Fix: pip install -e '.[dev]'"
  ((FAIL++)) || true
fi

# 4. Lint (non-blocking if ruff not installed)
if command -v ruff &>/dev/null; then
  if ruff check . --quiet 2>/dev/null; then
    echo "✓ ruff lint: clean"
    ((PASS++)) || true
  else
    echo "⚠ ruff lint: issues found (run: ruff check . for details)"
    ((WARN++)) || true
  fi
else
  echo "⚠ ruff not installed (optional — add to dev deps)"
  ((WARN++)) || true
fi

# 5. Test suite
echo ""
echo "--- Running test suite ---"
if pytest tests/ -q --tb=short; then
  echo ""
  echo "✓ All tests passing"
  ((PASS++)) || true
else
  echo ""
  echo "✗ Test suite has failures"
  ((FAIL++)) || true
fi

# Summary
echo ""
echo "=== Summary: ${PASS} passed · ${WARN} warnings · ${FAIL} failures ==="

if [ "$FAIL" -gt 0 ]; then
  echo "✗ FAILED — fix failures before starting new work"
  exit 1
else
  echo "✓ READY — safe to start development"
  exit 0
fi
