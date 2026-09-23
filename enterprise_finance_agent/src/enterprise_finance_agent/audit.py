"""Audit log: immutable run events with output fingerprint.

Every governed run appends ONE event. Sinks: JSONL file (production) or
in-memory (tests). Sensitive payloads are never stored — only hashes,
counts, codes and decisions. Retention/redaction policy lives with the host.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, Field

from .models import FinanceResult


class AuditEvent(BaseModel):
    run_id: str
    request_id: str
    user_id: str
    action_class: str
    authorized: bool
    evidence_count: int
    finding_codes: list[str] = Field(default_factory=list)
    requires_human_approval: bool = False
    output_fingerprint: str = ""
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


def fingerprint_result(result: FinanceResult) -> str:
    """sha256 over canonical summary+numbers. Re-runnable => same hash."""
    canonical = json.dumps(
        {
            "request_id": result.request_id,
            "summary": result.summary,
            "findings": sorted(f.code for f in result.findings),
            "evidence_count": len(result.evidence),
        },
        sort_keys=True,
        ensure_ascii=True,
    )
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
