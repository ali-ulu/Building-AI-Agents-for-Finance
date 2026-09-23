"""Typed contracts shared by the enterprise finance workflow."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class ActionClass(StrEnum):
    READ = "read"
    DRAFT = "draft"
    CONTROLLED_WRITE = "controlled_write"
    MONEY_MOVEMENT = "money_movement"
    PRIVILEGED_CHANGE = "privileged_change"


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Evidence(BaseModel):
    """One material piece of evidence used by an analysis."""

    source_system: str
    source_record_id: str | None = None
    as_of: datetime
    period: str | None = None
    entity: str | None = None
    currency: str | None = None
    unit: str | None = None
    value: Any
    data_quality: str = "unreviewed"


class FinanceRequest(BaseModel):
    """Normalized request entering the governed finance workflow."""

    request_id: str
    user_id: str
    intent: str
    action_class: ActionClass = ActionClass.READ
    risk_level: RiskLevel = RiskLevel.LOW
    entities: list[str] = Field(default_factory=list)
    period: str | None = None
    currency: str | None = None
    amount: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ValidationFinding(BaseModel):
    code: str
    severity: RiskLevel
    message: str


class FinanceResult(BaseModel):
    """Auditable result returned by the orchestrator."""

    request_id: str
    summary: str
    evidence: list[Evidence] = Field(default_factory=list)
    findings: list[ValidationFinding] = Field(default_factory=list)
    data_gaps: list[str] = Field(default_factory=list)
    requires_human_approval: bool = False
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
