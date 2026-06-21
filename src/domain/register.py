"""Append-only traceability register — pure domain logic for record serialisation."""
from __future__ import annotations
import json
from dataclasses import asdict
from pathlib import Path
from .models import TraceabilityRecord


def append_record(record: TraceabilityRecord, register_path: Path) -> None:
    """Append one record to the JSON register (creates file if absent)."""
    records: list[dict] = []
    if register_path.exists():
        records = json.loads(register_path.read_text())

    records.append(_serialise(record))
    register_path.write_text(json.dumps(records, indent=2))


def render_markdown(register_path: Path) -> str:
    """Render the register as a 5-column markdown table (Story, Commit, Author, Result, Date).

    Commit SHA is truncated to 7 characters. Status icon is ✅ for green, ❌ for red.
    Returns a placeholder string when the file is absent or contains an empty list —
    the caller will see '_No traceability records yet._'.
    """
    if not register_path.exists():
        return "_No traceability records yet._\n"

    records: list[dict] = json.loads(register_path.read_text())
    if not records:
        return "_No traceability records yet._\n"

    lines = [
        "| Story | Commit | Author | Result | Date |",
        "|-------|--------|--------|--------|------|",
    ]
    for r in records:
        gate = r.get("gate_result", {})
        status_icon = "✅" if gate.get("status") == "green" else "❌"
        sha = r.get("commit_sha", "")[:7]
        lines.append(
            f"| {r.get('story_id','')} "
            f"| `{sha}` "
            f"| {r.get('author','')} "
            f"| {status_icon} {gate.get('status','').upper()} "
            f"| {r.get('appended_at','')[:10]} |"
        )
    return "\n".join(lines) + "\n"


def _serialise(record: TraceabilityRecord) -> dict:
    """Serialise a TraceabilityRecord to a plain dict. asdict recurses into nested dataclasses."""
    return asdict(record)
