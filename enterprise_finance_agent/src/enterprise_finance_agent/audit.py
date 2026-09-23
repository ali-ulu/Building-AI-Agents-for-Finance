"""Finance audit surface. Storage + hashing live in core; the finance
result shape is adapted here so finance callers never touch core types."""

from __future__ import annotations

from governed_agent_core.audit import (
    AuditEvent as AuditEvent,
    AuditSink as AuditSink,
    JsonlAuditSink as JsonlAuditSink,
    MemoryAuditSink as MemoryAuditSink,
    fingerprint_mapping,
)

from .models import FinanceResult


def fingerprint_result(result: FinanceResult) -> str:
    """sha256 over canonical summary+numbers. Re-runnable => same hash."""
    return fingerprint_mapping(
        {
            "request_id": result.request_id,
            "summary": result.summary,
            "findings": sorted(f.code for f in result.findings),
            "evidence_count": len(result.evidence),
        }
    )
