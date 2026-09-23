"""Adversarial debate + finance-grade validation (deterministic side).

Pipeline order (V1):
  Actual vs Budget -> Root Cause -> Risk Scan -> Opportunity Scan
  -> Scenario -> Debate -> Validator -> CFO Report

Rules:
- Opportunity and Risk run INDEPENDENTLY on the same evidence.
- Debate never invents numbers; it only narrows the EUR range or
  escalates disagreement to the CFO pack.
- Validator runs deterministic checks before any LLM judge.

The round engine lives in governed_agent_core; finance finding types
are adapted here.
"""

from __future__ import annotations

from governed_agent_core.debate import (
    Challenge,
    Stake,
    debate_round as _debate_round,
)

from .models import (
    CfoPack,
    DebateRound,
    OpportunityFinding,
    RiskFindingDetail,
    RiskLevel,
    ValidationFinding,
)


def debate_round(
    opportunity: OpportunityFinding, risk: RiskFindingDetail
) -> DebateRound:
    """Single claim vs rebuttal round with explicit escalation rule."""
    outcome = _debate_round(
        Stake(
            label=opportunity.title,
            amount=opportunity.estimated_eur,
            confidence=opportunity.confidence,
            refs=opportunity.evidence_refs,
        ),
        Challenge(
            label=risk.title,
            amount=risk.estimated_eur,
            severity=risk.severity,
            refs=risk.evidence_refs,
            mitigation=risk.mitigation_hint,
        ),
    )
    return DebateRound(
        opportunity_claim=outcome.claim,
        risk_rebuttal=outcome.rebuttal,
        agreed_eur_range=outcome.agreed_range,
        escalate_to_cfo=outcome.escalate,
    )


def validate_cfo_pack(pack: CfoPack) -> list[ValidationFinding]:
    """Deterministic CFO-pack gates. LLM review comes after."""
    findings: list[ValidationFinding] = []
    if not pack.root_causes:
        findings.append(
            ValidationFinding(
                code="NO_ROOT_CAUSE",
                severity=RiskLevel.HIGH,
                message="Variance without quantified root causes is not CFO-grade.",
            )
        )
    if not pack.risks:
        findings.append(
            ValidationFinding(
                code="NO_RISK_SCAN",
                severity=RiskLevel.MEDIUM,
                message="Risk scan produced no findings; confirm inputs were attached.",
            )
        )
    if not pack.opportunities:
        findings.append(
            ValidationFinding(
                code="NO_OPPORTUNITY_SCAN",
                severity=RiskLevel.MEDIUM,
                message="Opportunity scan empty; DSO/DPO/DIO inputs may be missing.",
            )
        )
    if not pack.scenarios:
        findings.append(
            ValidationFinding(
                code="NO_SCENARIO",
                severity=RiskLevel.MEDIUM,
                message="No scenario output; at least FX/volume/energy cases expected.",
            )
        )
    for opp in pack.opportunities:
        if not opp.evidence_refs:
            findings.append(
                ValidationFinding(
                    code="UNPROVEN_OPPORTUNITY",
                    severity=RiskLevel.HIGH,
                    message=f"Opportunity '{opp.title}' has no evidence refs.",
                )
            )
    for r in pack.risks:
        if r.severity in {RiskLevel.HIGH, RiskLevel.CRITICAL} and not r.mitigation_hint:
            findings.append(
                ValidationFinding(
                    code="UNMITIGATED_RISK",
                    severity=RiskLevel.HIGH,
                    message=f"High risk '{r.title}' has no mitigation hint.",
                )
            )
    if not pack.recommended_actions:
        findings.append(
            ValidationFinding(
                code="NO_ACTION",
                severity=RiskLevel.HIGH,
                message="CFO pack without recommended actions is reporting, not finance.",
            )
        )
    return findings
