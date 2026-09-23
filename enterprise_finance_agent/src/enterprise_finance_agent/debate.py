"""Adversarial debate + finance-grade validation (deterministic side).

Pipeline order (V1):
  Actual vs Budget -> Root Cause -> Risk Scan -> Opportunity Scan
  -> Scenario -> Debate -> Validator -> CFO Report

Rules:
- Opportunity and Risk run INDEPENDENTLY on the same evidence.
- Debate never invents numbers; it only narrows the EUR range or
  escalates disagreement to the CFO pack.
- Validator runs deterministic checks before any LLM judge.
"""

from __future__ import annotations

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
    opp = opportunity.estimated_eur
    downside = risk.estimated_eur if risk.estimated_eur is not None else 0.0
    # If downside wipes >50% of upside, escalate instead of netting.
    escalate = downside > 0.5 * opp if opp > 0 else risk.severity in {
        RiskLevel.HIGH,
        RiskLevel.CRITICAL,
    }
    low = max(0.0, opp - downside)
    return DebateRound(
        opportunity_claim=f"{opportunity.title}: +{opp:,.0f} EUR ({opportunity.confidence})",
        risk_rebuttal=f"{risk.title}: -{downside:,.0f} EUR [{risk.severity}]",
        agreed_eur_range=(low, opp),
        escalate_to_cfo=escalate,
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
