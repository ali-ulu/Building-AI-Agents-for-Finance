"""Deterministic risk/opportunity signal scans over one company snapshot.

Thresholds come from finance-owned config so adapters and signal rules cannot
silently drift apart. LLMs may explain these signals but never override their
arithmetic.
"""

from __future__ import annotations

from pydantic import BaseModel

from .config import DEFAULT_FINANCE_POLICY, FinancePolicyConfig
from .models import (
    OpportunityFinding,
    RiskFindingDetail,
    RiskLevel,
    ValidationFinding,
)


class CompanySnapshot(BaseModel):
    entity: str
    period: str
    currency: str = "EUR"

    cash: float = 0.0
    minimum_cash_buffer: float = 0.0

    receivables_total: float = 0.0
    receivables_over_90: float = 0.0
    top_customer_receivables: float = 0.0

    inventory: float = 0.0
    inventory_target: float = 0.0

    annual_revenue: float = 0.0
    dso_days: float = 0.0
    dso_target_days: float = 0.0

    fx_exposure: float = 0.0
    interest_bearing_debt: float = 0.0
    variable_rate_debt_share: float = 0.0

    gross_margin_actual: float | None = None
    gross_margin_target: float | None = None

    procurement_spend: float = 0.0
    procurement_savings_rate: float = 0.0

    supplier_spend_total: float = 0.0
    top_supplier_spend: float = 0.0


def scan_risk_signals(
    snapshot: CompanySnapshot,
    source: str = "snapshot",
    policy: FinancePolicyConfig = DEFAULT_FINANCE_POLICY,
) -> list[RiskFindingDetail]:
    """Deterministic downside scan. Pure function, no model calls."""
    risks: list[RiskFindingDetail] = []
    cur = snapshot.currency

    if snapshot.cash < snapshot.minimum_cash_buffer:
        risks.append(
            RiskFindingDetail(
                title="Cash below minimum liquidity buffer",
                category="liquidity",
                severity=RiskLevel.CRITICAL,
                estimated_eur=snapshot.minimum_cash_buffer - snapshot.cash,
                evidence_refs=[source],
                mitigation_hint=(
                    f"Close the {snapshot.minimum_cash_buffer - snapshot.cash:,.0f} "
                    f"{cur} buffer gap before any discretionary spend."
                ),
            )
        )

    if snapshot.receivables_total > 0:
        share = snapshot.receivables_over_90 / snapshot.receivables_total
        if share >= policy.ar_high_share:
            risks.append(
                RiskFindingDetail(
                    title=f"90+ day receivables at {share:.1%} of AR",
                    category="collection",
                    severity=RiskLevel.HIGH,
                    estimated_eur=snapshot.receivables_over_90,
                    evidence_refs=[source],
                    mitigation_hint="Weekly collection sprint on 90+ balances.",
                )
            )
        elif share >= policy.ar_elevated_share:
            risks.append(
                RiskFindingDetail(
                    title=f"90+ day receivables elevated at {share:.1%}",
                    category="collection",
                    severity=RiskLevel.MEDIUM,
                    estimated_eur=snapshot.receivables_over_90,
                    evidence_refs=[source],
                )
            )

        concentration = snapshot.top_customer_receivables / snapshot.receivables_total
        if concentration >= policy.concentration_share:
            risks.append(
                RiskFindingDetail(
                    title=f"Top customer holds {concentration:.1%} of receivables",
                    category="concentration",
                    severity=RiskLevel.HIGH,
                    estimated_eur=snapshot.top_customer_receivables,
                    evidence_refs=[source],
                    mitigation_hint="Review credit limit and payment terms.",
                )
            )

    if snapshot.supplier_spend_total > 0:
        concentration = snapshot.top_supplier_spend / snapshot.supplier_spend_total
        if concentration >= policy.concentration_share:
            risks.append(
                RiskFindingDetail(
                    title=f"Top supplier takes {concentration:.1%} of spend",
                    category="supplier",
                    severity=RiskLevel.HIGH,
                    estimated_eur=snapshot.top_supplier_spend,
                    evidence_refs=[source],
                    mitigation_hint="Qualify a second source for critical SKUs.",
                )
            )

    if (
        snapshot.interest_bearing_debt > 0
        and snapshot.variable_rate_debt_share >= policy.variable_rate_share
    ):
        risks.append(
            RiskFindingDetail(
                title=(
                    f"{snapshot.variable_rate_debt_share:.0%} of debt "
                    "is variable-rate"
                ),
                category="rates",
                severity=RiskLevel.MEDIUM,
                estimated_eur=(
                    snapshot.interest_bearing_debt
                    * snapshot.variable_rate_debt_share
                ),
                evidence_refs=[source],
            )
        )

    if snapshot.fx_exposure != 0:
        risks.append(
            RiskFindingDetail(
                title="Open foreign-exchange exposure",
                category="fx",
                severity=RiskLevel.MEDIUM,
                estimated_eur=abs(snapshot.fx_exposure),
                evidence_refs=[source],
            )
        )

    return risks


def scan_opportunity_signals(
    snapshot: CompanySnapshot, source: str = "snapshot"
) -> list[OpportunityFinding]:
    """Deterministic upside scan with explicit overlap groups."""
    opportunities: list[OpportunityFinding] = []

    if snapshot.annual_revenue > 0 and snapshot.dso_days > snapshot.dso_target_days:
        gap = snapshot.dso_days - snapshot.dso_target_days
        opportunities.append(
            OpportunityFinding(
                title="Release cash by reducing DSO",
                category="cash",
                estimated_eur=snapshot.annual_revenue / 365 * gap,
                confidence="high",
                assumptions=[
                    f"DSO {snapshot.dso_days:.1f} -> {snapshot.dso_target_days:.1f} "
                    "without losing customers"
                ],
                evidence_refs=[source],
                overlap_group="receivables_cash",
            )
        )

    if snapshot.inventory > snapshot.inventory_target:
        opportunities.append(
            OpportunityFinding(
                title="Release working capital from excess inventory",
                category="cash",
                estimated_eur=snapshot.inventory - snapshot.inventory_target,
                confidence="high",
                assumptions=["Obsolete stock is saleable or returnable"],
                evidence_refs=[source],
                overlap_group="inventory_cash",
            )
        )

    if snapshot.receivables_over_90 > 0:
        opportunities.append(
            OpportunityFinding(
                title="Recover aged receivables",
                category="cash",
                estimated_eur=snapshot.receivables_over_90,
                confidence="medium",
                assumptions=["Focused 90+ collection recovers balances in full"],
                evidence_refs=[source],
                overlap_group="receivables_cash",
            )
        )

    if (
        snapshot.gross_margin_actual is not None
        and snapshot.gross_margin_target is not None
        and snapshot.annual_revenue > 0
        and snapshot.gross_margin_actual < snapshot.gross_margin_target
    ):
        gap = snapshot.gross_margin_target - snapshot.gross_margin_actual
        opportunities.append(
            OpportunityFinding(
                title="Close the gross-margin gap",
                category="margin",
                estimated_eur=snapshot.annual_revenue * gap,
                confidence="medium",
                assumptions=["Decompose into price, mix, volume, input cost"],
                evidence_refs=[source],
                overlap_group="margin_improvement",
            )
        )

    if snapshot.procurement_spend > 0 and snapshot.procurement_savings_rate > 0:
        opportunities.append(
            OpportunityFinding(
                title="Procurement savings envelope",
                category="cost",
                estimated_eur=(
                    snapshot.procurement_spend * snapshot.procurement_savings_rate
                ),
                confidence="medium",
                assumptions=["Approved savings rate applies to addressable spend"],
                evidence_refs=[source],
                overlap_group="margin_improvement",
            )
        )

    return opportunities


def check_snapshot_consistency(snapshot: CompanySnapshot) -> list[ValidationFinding]:
    """Cross-field sanity gates. Returns findings; empty means consistent."""
    findings: list[ValidationFinding] = []

    for field in ("entity", "period", "currency"):
        if not getattr(snapshot, field).strip():
            findings.append(
                ValidationFinding(
                    code=f"MISSING_{field.upper()}",
                    severity=RiskLevel.CRITICAL,
                    message=f"{field} is required.",
                )
            )

    if snapshot.receivables_over_90 > snapshot.receivables_total:
        findings.append(
            ValidationFinding(
                code="AR_AGING_INCONSISTENT",
                severity=RiskLevel.CRITICAL,
                message="90+ receivables cannot exceed total receivables.",
            )
        )
    if snapshot.top_customer_receivables > snapshot.receivables_total:
        findings.append(
            ValidationFinding(
                code="AR_CONCENTRATION_INCONSISTENT",
                severity=RiskLevel.CRITICAL,
                message="Top-customer receivables cannot exceed total receivables.",
            )
        )
    if snapshot.top_supplier_spend > snapshot.supplier_spend_total:
        findings.append(
            ValidationFinding(
                code="SUPPLIER_CONCENTRATION_INCONSISTENT",
                severity=RiskLevel.CRITICAL,
                message="Top-supplier spend cannot exceed total supplier spend.",
            )
        )
    if not 0 <= snapshot.variable_rate_debt_share <= 1:
        findings.append(
            ValidationFinding(
                code="INVALID_VARIABLE_RATE_SHARE",
                severity=RiskLevel.CRITICAL,
                message="Variable-rate debt share must be between 0 and 1.",
            )
        )
    for name in ("gross_margin_actual", "gross_margin_target"):
        margin = getattr(snapshot, name)
        if margin is not None and not -1 <= margin <= 1:
            findings.append(
                ValidationFinding(
                    code="INVALID_MARGIN",
                    severity=RiskLevel.CRITICAL,
                    message=f"{name} must be a decimal between -1 and 1.",
                )
            )

    return findings
