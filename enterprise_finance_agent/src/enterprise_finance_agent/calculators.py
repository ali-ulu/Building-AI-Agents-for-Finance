"""Deterministic finance calculators.

LLMs may summarize and interpret, but they must never compute these.
Every function here is pure, tested, and carries no model dependency.
All money values are floats in stated currency; days are actual/365.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class VarianceLine(BaseModel):
    label: str
    budget: float
    actual: float

    @property
    def variance(self) -> float:
        return self.actual - self.budget


class VarianceBridge(BaseModel):
    lines: list[VarianceLine]
    total_budget: float
    total_actual: float
    calculated_variance: float
    headline_variance: float
    total_variance: float
    explained: float
    unexplained: float


def build_variance_bridge(
    lines: list[VarianceLine],
    headline_variance: float | None = None,
) -> VarianceBridge:
    """Build a bridge against an independently supplied headline variance.

    Without a headline, the function remains backward compatible and treats the
    supplied driver lines as the complete bridge. With a headline, unexplained
    is headline variance minus the sum of explained driver variances.
    """
    total_budget = sum(line.budget for line in lines)
    total_actual = sum(line.actual for line in lines)
    calculated_variance = total_actual - total_budget
    explained = sum(line.variance for line in lines)
    headline = calculated_variance if headline_variance is None else headline_variance

    return VarianceBridge(
        lines=lines,
        total_budget=total_budget,
        total_actual=total_actual,
        calculated_variance=calculated_variance,
        headline_variance=headline,
        total_variance=headline,
        explained=explained,
        unexplained=headline - explained,
    )


class WorkingCapitalInput(BaseModel):
    annual_revenue: float = Field(gt=0)
    annual_cogs: float = Field(gt=0)
    annual_purchases: float = Field(gt=0)
    receivables: float = Field(ge=0)
    inventory: float = Field(ge=0)
    payables: float = Field(ge=0)


class WorkingCapitalMetrics(BaseModel):
    dso: float
    dio: float
    dpo: float
    ccc: float


def working_capital_metrics(data: WorkingCapitalInput) -> WorkingCapitalMetrics:
    """DSO / DIO / DPO / CCC on actual/365 basis."""
    dso = data.receivables / data.annual_revenue * 365.0
    dio = data.inventory / data.annual_cogs * 365.0
    dpo = data.payables / data.annual_purchases * 365.0
    return WorkingCapitalMetrics(dso=dso, dio=dio, dpo=dpo, ccc=dso + dio - dpo)


def cash_release_for_dso_reduction(
    annual_revenue: float, current_dso: float, target_dso: float
) -> float:
    """Cash freed by pulling DSO down."""
    if target_dso >= current_dso:
        return 0.0
    return annual_revenue / 365.0 * (current_dso - target_dso)


def cash_release_for_dio_reduction(
    annual_cogs: float, current_dio: float, target_dio: float
) -> float:
    """Cash freed by reducing inventory days."""
    if target_dio >= current_dio:
        return 0.0
    return annual_cogs / 365.0 * (current_dio - target_dio)


class FxExposure(BaseModel):
    net_foreign_currency_exposure: float
    base_rate: float = Field(gt=0)


def fx_ebitda_impact(exposure: FxExposure, rate_move_pct: float) -> float:
    """Linear translation impact: exposure * move. No convexity invented."""
    return exposure.net_foreign_currency_exposure * (rate_move_pct / 100.0)


def scenario_ebitda(
    base_ebitda: float,
    volume_move_pct: float = 0.0,
    contribution_margin_ratio: float = 0.0,
    cost_shock: float = 0.0,
    fx_impact: float = 0.0,
    *,
    revenue_base: float | None = None,
) -> float:
    """Deterministic EBITDA scenario.

    Volume impact is revenue_base * volume move * contribution margin.
    EBITDA is never used as a proxy for revenue. A non-zero volume move without
    a revenue base is rejected instead of silently producing a misleading value.
    """
    if volume_move_pct and revenue_base is None:
        raise ValueError("revenue_base is required when volume_move_pct is non-zero")

    volume_effect = 0.0
    if volume_move_pct:
        volume_effect = (
            revenue_base
            * contribution_margin_ratio
            * (volume_move_pct / 100.0)
        )

    return base_ebitda + volume_effect - cost_shock + fx_impact
