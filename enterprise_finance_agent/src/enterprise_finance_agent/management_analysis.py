"""Deterministic management-finance analytics.

Implements:
actual vs budget -> root cause -> risk scan -> opportunity scan ->
scenario analysis -> validation -> CFO pack

LLMs may explain these outputs, but they do not own the arithmetic.
"""

from __future__ import annotations

from math import isfinite

from pydantic import BaseModel, Field

from .models import RiskLevel, ValidationFinding


class PLLine(BaseModel):
    name: str
    actual: float
    budget: float
    kind: str = "cost"  # "revenue" or "cost"


class FinanceSnapshot(BaseModel):
    entity: str
    period: str
    currency: str
    pl_lines: list[PLLine] = Field(default_factory=list)

    cash: float
    minimum_cash_buffer: float

    receivables_total: float
    receivables_over_90: float
    top_customer_receivables: float

    payables_total: float

    inventory: float
    inventory_target: float

    annual_revenue: float
    dso_days: float
    dso_target_days: float

    fx_exposure: float = 0.0
    interest_bearing_debt: float = 0.0
    variable_rate_debt_share: float = 0.0


class VarianceDriver(BaseModel):
    name: str
    actual: float
    budget: float
    variance: float
    unfavorable_impact: float


class RiskSignal(BaseModel):
    code: str
    level: RiskLevel
    title: str
    evidence: str
    estimated_exposure: float | None = None


class OpportunitySignal(BaseModel):
    code: str
    title: str
    rationale: str
    estimated_value: float | None = None
    confidence: str = "medium"


class ScenarioAssumption(BaseModel):
    name: str
    change_pct: float
    exposure: float


class ScenarioResult(BaseModel):
    name: str
    change_pct: float
    estimated_pnl_impact: float


class ManagementAnalysis(BaseModel):
    entity: str
    period: str
    currency: str
    variance_drivers: list[VarianceDriver]
    risks: list[RiskSignal]
    opportunities: list[OpportunitySignal]
    scenarios: list[ScenarioResult]
    findings: list[ValidationFinding]
    is_valid: bool


def analyze_management_finance(
    snapshot: FinanceSnapshot,
    scenarios: list[ScenarioAssumption] | None = None,
) -> ManagementAnalysis:
    """Run the deterministic management-finance analysis."""

    variance_drivers = _calculate_variances(snapshot.pl_lines)
    risks = _scan_risks(snapshot)
    opportunities = _scan_opportunities(snapshot)
    scenario_results = _run_scenarios(scenarios or [])
    findings = _validate(snapshot, variance_drivers, risks, opportunities)

    return ManagementAnalysis(
        entity=snapshot.entity,
        period=snapshot.period,
        currency=snapshot.currency,
        variance_drivers=variance_drivers,
        risks=risks,
        opportunities=opportunities,
        scenarios=scenario_results,
        findings=findings,
        is_valid=not any(
            f.severity in {RiskLevel.HIGH, RiskLevel.CRITICAL}
            for f in findings
        ),
    )


def _calculate_variances(lines: list[PLLine]) -> list[VarianceDriver]:
    drivers: list[VarianceDriver] = []
    for line in lines:
        variance = line.actual - line.budget
        unfavorable = -variance if line.kind == "revenue" else variance
        drivers.append(
            VarianceDriver(
                name=line.name,
                actual=line.actual,
                budget=line.budget,
                variance=variance,
                unfavorable_impact=unfavorable,
            )
        )

    return sorted(
        drivers,
        key=lambda d: abs(d.unfavorable_impact),
        reverse=True,
    )


def _scan_risks(snapshot: FinanceSnapshot) -> list[RiskSignal]:
    risks: list[RiskSignal] = []

    if snapshot.cash < snapshot.minimum_cash_buffer:
        gap = snapshot.minimum_cash_buffer - snapshot.cash
        risks.append(
            RiskSignal(
                code="LIQUIDITY_BUFFER_BREACH",
                level=RiskLevel.CRITICAL,
                title="Cash below minimum liquidity buffer",
                evidence=(
                    f"Cash {snapshot.cash:,.0f} vs minimum buffer "
                    f"{snapshot.minimum_cash_buffer:,.0f} {snapshot.currency}"
                ),
                estimated_exposure=gap,
            )
        )

    if snapshot.receivables_total > 0:
        overdue_share = snapshot.receivables_over_90 / snapshot.receivables_total
        if overdue_share >= 0.20:
            risks.append(
                RiskSignal(
                    code="AR_AGING_HIGH",
                    level=RiskLevel.HIGH,
                    title="90+ day receivables concentration is high",
                    evidence=f"90+ AR share is {overdue_share:.1%}",
                    estimated_exposure=snapshot.receivables_over_90,
                )
            )
        elif overdue_share >= 0.10:
            risks.append(
                RiskSignal(
                    code="AR_AGING_ELEVATED",
                    level=RiskLevel.MEDIUM,
                    title="90+ day receivables are elevated",
                    evidence=f"90+ AR share is {overdue_share:.1%}",
                    estimated_exposure=snapshot.receivables_over_90,
                )
            )

        customer_concentration = (
            snapshot.top_customer_receivables / snapshot.receivables_total
        )
        if customer_concentration >= 0.35:
            risks.append(
                RiskSignal(
                    code="CUSTOMER_CONCENTRATION",
                    level=RiskLevel.HIGH,
                    title="Receivables are concentrated in one customer",
                    evidence=(
                        f"Top customer represents "
                        f"{customer_concentration:.1%} of receivables"
                    ),
                    estimated_exposure=snapshot.top_customer_receivables,
                )
            )

    if (
        snapshot.interest_bearing_debt > 0
        and snapshot.variable_rate_debt_share >= 0.50
    ):
        risks.append(
            RiskSignal(
                code="RATE_EXPOSURE",
                level=RiskLevel.MEDIUM,
                title="Large variable-rate debt exposure",
                evidence=(
                    f"{snapshot.variable_rate_debt_share:.1%} of "
                    "interest-bearing debt is variable-rate"
                ),
                estimated_exposure=(
                    snapshot.interest_bearing_debt
                    * snapshot.variable_rate_debt_share
                ),
            )
        )

    if snapshot.fx_exposure != 0:
        risks.append(
            RiskSignal(
                code="FX_EXPOSURE",
                level=RiskLevel.MEDIUM,
                title="Open foreign-exchange exposure exists",
                evidence=(
                    f"Net open FX exposure is "
                    f"{snapshot.fx_exposure:,.0f} {snapshot.currency}"
                ),
                estimated_exposure=abs(snapshot.fx_exposure),
            )
        )

    return risks


def _scan_opportunities(snapshot: FinanceSnapshot) -> list[OpportunitySignal]:
    opportunities: list[OpportunitySignal] = []

    if (
        snapshot.annual_revenue > 0
        and snapshot.dso_days > snapshot.dso_target_days
    ):
        days_reducible = snapshot.dso_days - snapshot.dso_target_days
        cash_release = snapshot.annual_revenue / 365 * days_reducible
        opportunities.append(
            OpportunitySignal(
                code="DSO_REDUCTION",
                title="Release cash by reducing DSO",
                rationale=(
                    f"DSO is {snapshot.dso_days:.1f} days vs target "
                    f"{snapshot.dso_target_days:.1f}; reducing the gap "
                    "would release working capital."
                ),
                estimated_value=cash_release,
                confidence="high",
            )
        )

    if snapshot.inventory > snapshot.inventory_target:
        release = snapshot.inventory - snapshot.inventory_target
        opportunities.append(
            OpportunitySignal(
                code="INVENTORY_RELEASE",
                title="Release working capital from excess inventory",
                rationale=(
                    f"Inventory exceeds target by "
                    f"{release:,.0f} {snapshot.currency}."
                ),
                estimated_value=release,
                confidence="high",
            )
        )

    if snapshot.receivables_over_90 > 0:
        opportunities.append(
            OpportunitySignal(
                code="COLLECTION_RECOVERY",
                title="Prioritize recovery of aged receivables",
                rationale=(
                    "Focused collections on 90+ day balances may improve "
                    "cash conversion and reduce credit exposure."
                ),
                estimated_value=snapshot.receivables_over_90,
                confidence="medium",
            )
        )

    return opportunities


def _run_scenarios(
    assumptions: list[ScenarioAssumption],
) -> list[ScenarioResult]:
    results: list[ScenarioResult] = []
    for assumption in assumptions:
        impact = assumption.exposure * assumption.change_pct
        results.append(
            ScenarioResult(
                name=assumption.name,
                change_pct=assumption.change_pct,
                estimated_pnl_impact=impact,
            )
        )
    return results


def _validate(
    snapshot: FinanceSnapshot,
    variances: list[VarianceDriver],
    risks: list[RiskSignal],
    opportunities: list[OpportunitySignal],
) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []

    if not snapshot.entity.strip():
        findings.append(
            ValidationFinding(
                code="MISSING_ENTITY",
                severity=RiskLevel.CRITICAL,
                message="Entity is required.",
            )
        )

    if not snapshot.period.strip():
        findings.append(
            ValidationFinding(
                code="MISSING_PERIOD",
                severity=RiskLevel.CRITICAL,
                message="Reporting period is required.",
            )
        )

    if not snapshot.currency.strip():
        findings.append(
            ValidationFinding(
                code="MISSING_CURRENCY",
                severity=RiskLevel.CRITICAL,
                message="Currency is required.",
            )
        )

    numeric_fields = {
        "cash": snapshot.cash,
        "minimum_cash_buffer": snapshot.minimum_cash_buffer,
        "receivables_total": snapshot.receivables_total,
        "receivables_over_90": snapshot.receivables_over_90,
        "top_customer_receivables": snapshot.top_customer_receivables,
        "payables_total": snapshot.payables_total,
        "inventory": snapshot.inventory,
        "inventory_target": snapshot.inventory_target,
        "annual_revenue": snapshot.annual_revenue,
        "dso_days": snapshot.dso_days,
        "dso_target_days": snapshot.dso_target_days,
        "fx_exposure": snapshot.fx_exposure,
        "interest_bearing_debt": snapshot.interest_bearing_debt,
        "variable_rate_debt_share": snapshot.variable_rate_debt_share,
    }

    for name, value in numeric_fields.items():
        if not isfinite(value):
            findings.append(
                ValidationFinding(
                    code="NON_FINITE_VALUE",
                    severity=RiskLevel.CRITICAL,
                    message=f"{name} must be finite.",
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

    if not 0 <= snapshot.variable_rate_debt_share <= 1:
        findings.append(
            ValidationFinding(
                code="INVALID_VARIABLE_RATE_SHARE",
                severity=RiskLevel.CRITICAL,
                message="Variable-rate debt share must be between 0 and 1.",
            )
        )

    if not variances:
        findings.append(
            ValidationFinding(
                code="NO_VARIANCE_DATA",
                severity=RiskLevel.HIGH,
                message="No P&L lines were supplied for variance analysis.",
            )
        )

    if not risks:
        findings.append(
            ValidationFinding(
                code="NO_RISK_SIGNAL",
                severity=RiskLevel.LOW,
                message="No configured deterministic risk threshold was breached.",
            )
        )

    if not opportunities:
        findings.append(
            ValidationFinding(
                code="NO_OPPORTUNITY_SIGNAL",
                severity=RiskLevel.LOW,
                message="No configured deterministic opportunity was detected.",
            )
        )

    return findings
