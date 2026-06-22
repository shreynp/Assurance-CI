#!/usr/bin/env bash
set -e

echo "=== Pre-commit validation ==="

# 1. Secrets check — fail hard if detected
if git diff --cached --unified=0 | grep -qiE '(sk-ant-[a-zA-Z0-9]{10}|ANTHROPIC_API_KEY\s*=\s*["\047][^"\047]+|password\s*=\s*["\047][^"\047]{8})'; then
  echo "✗ Possible secret detected in staged changes — aborting commit"
  echo "  Remove the secret and try again"
  exit 1
fi
echo "✓ No secrets detected in staged diff"

# 2. Domain purity check — warn if I/O imported in src/domain/
if git diff --cached --name-only | grep -q "^src/domain/"; then
  if git diff --cached -- "src/domain/*.py" | grep -qE "^\\+.*(import os|import subprocess|open\(|requests\.|httpx\.|anthropic\.)"; then
    echo "✗ Domain purity violation: src/domain/ file imports I/O or external calls"
    echo "  Move I/O to scripts/"
    exit 1
  fi
  echo "✓ Domain purity check passed"
fi

echo "✓ Pre-commit validation passed"
exit 0
