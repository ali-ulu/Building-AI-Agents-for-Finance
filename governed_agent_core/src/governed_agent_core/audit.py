"""Audit log: immutable run events with output fingerprint.

One event per governed run. Sinks: JSONL file (production) or in-memory
(tests). Payloads are never stored — only hashes, counts, codes and
decisions. Retention/redaction policy lives with the host app.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, Field


class AuditEvent(BaseModel):
    run_id: str
    request_id: str
    principal_id: str
    action_class: str
    authorized: bool
    evidence_count: int
    finding_codes: list[str] = Field(default_factory=list)
    requires_human_approval: bool = False
    output_fingerprint: str = ""
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


def fingerprint_mapping(data: dict) -> str:
    """sha256 over canonical JSON. Same input => same hash, always."""
    canonical = json.dumps(data, sort_keys=True, ensure_ascii=True)
    return "sha256:" + hashlib.sha256(canonical.encode()).hexdigest()[:16]


class AuditSink(Protocol):
    def append(self, event: AuditEvent) -> None: ...


class MemoryAuditSink:
    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    def append(self, event: AuditEvent) -> None:
        self.events.append(event)


class JsonlAuditSink:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, event: AuditEvent) -> None:
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(event.model_dump_json() + "\n")
