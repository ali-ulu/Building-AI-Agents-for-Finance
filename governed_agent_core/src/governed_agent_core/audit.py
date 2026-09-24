"""Tamper-evident audit log with output fingerprints.

One event is appended per governed run. JSONL storage uses a cryptographic
hash chain: each event commits to the previous event hash. This does not make
a local file physically immutable, but post-write edits become detectable by
verify_jsonl_audit_chain().
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
    previous_hash: str = ""
    event_hash: str = ""
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


def fingerprint_mapping(data: dict) -> str:
    """sha256 over canonical JSON. Same input => same hash, always."""
    canonical = json.dumps(data, sort_keys=True, ensure_ascii=True)
    return "sha256:" + hashlib.sha256(canonical.encode()).hexdigest()[:16]


def _event_payload(event: AuditEvent) -> dict:
    return event.model_dump(
        mode="json",
        exclude={"previous_hash", "event_hash"},
    )


def _event_hash(event: AuditEvent, previous_hash: str) -> str:
    canonical = json.dumps(
        {
            "previous_hash": previous_hash,
            "event": _event_payload(event),
        },
        sort_keys=True,
        ensure_ascii=True,
        separators=(",", ":"),
    )
    return "sha256:" + hashlib.sha256(canonical.encode()).hexdigest()


def _chain_event(event: AuditEvent, previous_hash: str) -> AuditEvent:
    chained = event.model_copy(deep=True)
    chained.previous_hash = previous_hash
    chained.event_hash = _event_hash(chained, previous_hash)
    return chained


class AuditSink(Protocol):
    def append(self, event: AuditEvent) -> None: ...


class MemoryAuditSink:
    def __init__(self) -> None:
        self.events: list[AuditEvent] = []
        self._last_hash = ""

    def append(self, event: AuditEvent) -> None:
        chained = _chain_event(event, self._last_hash)
        self.events.append(chained)
        self._last_hash = chained.event_hash


class JsonlAuditSink:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._last_hash = self._read_last_hash()

    def _read_last_hash(self) -> str:
        if not self.path.exists():
            return ""
        last = ""
        with open(self.path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    last = line
        if not last:
            return ""
        try:
            event = AuditEvent.model_validate_json(last)
            return event.event_hash
        except Exception:
            return ""

    def append(self, event: AuditEvent) -> None:
        chained = _chain_event(event, self._last_hash)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(chained.model_dump_json() + "\n")
        self._last_hash = chained.event_hash


def verify_jsonl_audit_chain(path: str | Path) -> bool:
    """Return True only when every event hash and link verifies."""
    path = Path(path)
    if not path.exists():
        return True

    previous_hash = ""
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                event = AuditEvent.model_validate_json(line)
                if event.previous_hash != previous_hash:
                    return False
                if not event.event_hash:
                    return False
                if event.event_hash != _event_hash(event, previous_hash):
                    return False
                previous_hash = event.event_hash
    except (OSError, ValueError, json.JSONDecodeError):
        return False

    return True
