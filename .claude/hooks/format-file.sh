#!/usr/bin/env bash
# PostToolUse formatter — silently formats Python files after Edit/Write
FILE="${1:-}"
[ -z "$FILE" ] && exit 0

if [[ "$FILE" == *.py ]]; then
  if command -v ruff &>/dev/null; then
    ruff format "$FILE" --quiet 2>/dev/null || true
  fi
fi

exit 0
