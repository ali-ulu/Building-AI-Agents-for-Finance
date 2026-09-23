"""Typed contracts shared by the enterprise finance workflow."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from governed_agent_core import ActionClass, RiskLevel
from pydantic import BaseModel, Field


__all__ = ["ActionClass", "RiskLevel"]


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


class OpportunityFinding(BaseModel):
    """One quantified upside. Amount must come from calculators, not LLM."""

    title: str
    category: str = Field(
        description="revenue | cost | margin | cash | pricing | sourcing | market"
    )
    estimated_eur: float
    confidence: str = Field(description="high | medium | low")
    assumptions: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)


class RiskFindingDetail(BaseModel):
    """One quantified downside / control flag."""

    title: str
    category: str = Field(
        description="liquidity | concentration | fx | rates | debt | covenant | margin | collection | stock | ops"
    )
    severity: RiskLevel
    estimated_eur: float | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    mitigation_hint: str | None = None


class ScenarioInput(BaseModel):
    name: str
    volume_move_pct: float = 0.0
    cost_shock_eur: float = 0.0
    fx_move_pct: float = 0.0
    rate_move_bps: int = 0


class ScenarioOutput(BaseModel):
    name: str
    ebitda_impact_eur: float
    cash_impact_eur: float = 0.0
    assumptions: list[str] = Field(default_factory=list)


class DebateRound(BaseModel):
    """One adversarial round: opportunity claims, risk rebuts."""

    opportunity_claim: str
    risk_rebuttal: str
    agreed_eur_range: tuple[float, float] | None = None
    escalate_to_cfo: bool = False


class CfoPack(BaseModel):
    """Structured CFO output: explain + risk + opportunity + scenario + action."""

    period: str
    entity: str | None = None
    currency: str = "EUR"
    headline_variance_eur: float
    root_causes: list[str] = Field(default_factory=list)
    risks: list[RiskFindingDetail] = Field(default_factory=list)
    opportunities: list[OpportunityFinding] = Field(default_factory=list)
    scenarios: list[ScenarioOutput] = Field(default_factory=list)
    debate: list[DebateRound] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
