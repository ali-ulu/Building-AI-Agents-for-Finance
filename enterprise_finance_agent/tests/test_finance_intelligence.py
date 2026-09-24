"""Finance intelligence: calculators + debate + CFO-pack gates."""

import pytest

from enterprise_finance_agent.calculators import (
    VarianceLine,
    WorkingCapitalInput,
    build_variance_bridge,
    cash_release_for_dso_reduction,
    fx_ebitda_impact,
    FxExposure,
    scenario_ebitda,
    working_capital_metrics,
)
from enterprise_finance_agent.debate import debate_round, validate_cfo_pack
from enterprise_finance_agent.models import (
    CfoPack,
    OpportunityFinding,
    RiskFindingDetail,
    RiskLevel,
    ScenarioOutput,
)


def test_variance_bridge_backward_compatible_when_complete():
    lines = [
        VarianceLine(label="raw material", budget=0.0, actual=420_000.0),
        VarianceLine(label="volume", budget=0.0, actual=-510_000.0),
        VarianceLine(label="fx", budget=0.0, actual=-180_000.0),
    ]
    bridge = build_variance_bridge(lines)
    assert bridge.total_variance == -270_000.0
    assert bridge.unexplained == 0.0


def test_variance_bridge_uses_independent_headline():
    lines = [
        VarianceLine(label="raw material", budget=0.0, actual=-420_000.0),
        VarianceLine(label="volume", budget=0.0, actual=-510_000.0),
        VarianceLine(label="fx", budget=0.0, actual=-180_000.0),
    ]
    bridge = build_variance_bridge(lines, headline_variance=-1_200_000.0)
    assert bridge.explained == -1_110_000.0
    assert bridge.unexplained == -90_000.0
    assert bridge.total_variance == -1_200_000.0


def test_volume_scenario_uses_revenue_not_ebitda_proxy():
    result = scenario_ebitda(
        base_ebitda=10_000_000.0,
        volume_move_pct=-8.0,
        contribution_margin_ratio=0.35,
        revenue_base=100_000_000.0,
    )
    assert result == 7_200_000.0


def test_volume_scenario_requires_revenue_base():
    with pytest.raises(ValueError, match="revenue_base"):
        scenario_ebitda(
            base_ebitda=10_000_000.0,
            volume_move_pct=-8.0,
            contribution_margin_ratio=0.35,
        )


def test_dso_cash_release_matches_example():
    revenue = 1_800_000.0 / 7.0 * 365.0
    release = cash_release_for_dso_reduction(revenue, 52, 45)
    assert abs(release - 1_800_000.0) < 1.0
    assert cash_release_for_dso_reduction(revenue, 52, 52) == 0.0


def test_working_capital_metrics():
    m = working_capital_metrics(
        WorkingCapitalInput(
            annual_revenue=93_857_142.0,
            annual_cogs=60_000_000.0,
            annual_purchases=55_000_000.0,
            receivables=13_371_428.0,
            inventory=8_219_178.0,
            payables=7_534_246.0,
        )
    )
    assert abs(m.dso - 52.0) < 0.5
    assert m.ccc == m.dso + m.dio - m.dpo


def test_fx_impact_linear():
    impact = fx_ebitda_impact(
        FxExposure(net_foreign_currency_exposure=4_000_000.0, base_rate=1.08),
        5.0,
    )
    assert impact == 200_000.0


def test_debate_escalates_when_downside_dominates():
    opp = OpportunityFinding(
        title="New plant margin lift",
        category="margin",
        estimated_eur=1_000_000.0,
        confidence="medium",
        evidence_refs=["capex_model:v3"],
    )
    risk = RiskFindingDetail(
        title="Demand -15% leaves capacity idle, IRR 14%->6%",
        category="ops",
        severity=RiskLevel.HIGH,
        estimated_eur=700_000.0,
    )
    round_ = debate_round(opp, risk)
    assert round_.escalate_to_cfo is True
    assert round_.agreed_eur_range == (300_000.0, 1_000_000.0)


def test_validator_flags_unproven_opportunity_and_missing_action():
    pack = CfoPack(
        period="2026-09",
        headline_variance_eur=-1_200_000.0,
        root_causes=["raw +420k", "volume -510k", "fx -180k"],
        risks=[
            RiskFindingDetail(
                title="90+ AR 640k concentration",
                category="collection",
                severity=RiskLevel.HIGH,
                estimated_eur=640_000.0,
                mitigation_hint="Weekly collection sprint on top-2 accounts.",
            )
        ],
        opportunities=[
            OpportunityFinding(
                title="DSO 52->45",
                category="cash",
                estimated_eur=1_800_000.0,
                confidence="high",
                evidence_refs=[],
            )
        ],
        scenarios=[
            ScenarioOutput(name="EUR/USD +5%", ebitda_impact_eur=200_000.0)
        ],
        recommended_actions=[],
    )
    codes = {f.code for f in validate_cfo_pack(pack)}
    assert "UNPROVEN_OPPORTUNITY" in codes
    assert "NO_ACTION" in codes
