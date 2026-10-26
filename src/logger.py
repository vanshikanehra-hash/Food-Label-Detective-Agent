"""
Structured logging of agent runs.

Every analysis is appended to logs/agent_runs.jsonl as one JSON object per line.
This gives an auditable trail of the agent's steps and outputs, which the
capstone rubric asks for ("Logs of agent steps or sample scenarios included").
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
LOG_FILE = os.path.join(LOG_DIR, "agent_runs.jsonl")


def log_run(record: dict) -> None:
    """Append a single agent run record to the JSONL log."""
    os.makedirs(LOG_DIR, exist_ok=True)
    record = {"timestamp": datetime.now(timezone.utc).isoformat(), **record}
    with open(LOG_FILE, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def read_runs(limit: int = 50) -> list[dict]:
    """Return the most recent run records (newest last)."""
    if not os.path.exists(LOG_FILE):
        return []
    with open(LOG_FILE, encoding="utf-8") as fh:
        lines = fh.readlines()
    records = []
    for line in lines[-limit:]:
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records
