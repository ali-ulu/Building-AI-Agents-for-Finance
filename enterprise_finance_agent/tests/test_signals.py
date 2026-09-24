"""Signal engine, centralized policy and opportunity aggregation tests."""

from enterprise_finance_agent.adapters import ArCustomerBalance, summarize_ar_aging
from enterprise_finance_agent.config import FinancePolicyConfig
from enterprise_finance_agent.opportunities import summarize_opportunities
from enterprise_finance_agent.reporting import format_cfo_pack_markdown
from enterprise_finance_agent.signals import (
    CompanySnapshot,
    check_snapshot_consistency,
    scan_opportunity_signals,
    scan_risk_signals,
)


def _full_snapshot() -> CompanySnapshot:
    return CompanySnapshot(
        entity="DemoCo",
        period="2026-09",
        cash=400_000.0,
        minimum_cash_buffer=500_000.0,
        receivables_total=1_000_000.0,
        receivables_over_90=250_000.0,
        top_customer_receivables=400_000.0,
        inventory=9_000_000.0,
        inventory_target=8_000_000.0,
        annual_revenue=93_857_142.0,
        dso_days=52.0,
        dso_target_days=45.0,
        fx_exposure=4_000_000.0,
        interest_bearing_debt=10_000_000.0,
        variable_rate_debt_share=0.6,
        gross_margin_actual=0.30,
        gross_margin_target=0.33,
        procurement_spend=55_000_000.0,
        procurement_savings_rate=0.02,
        supplier_spend_total=55_000_000.0,
        top_supplier_spend=22_000_000.0,
    )


def test_risk_scan_fires_all_configured_rules():
    codes = {
        r.title: r
        for r in scan_risk_signals(_full_snapshot(), source="t")
    }
    assert any("liquidity buffer" in t for t in codes)
    assert any("90+" in t for t in codes)
    assert any("Top customer" in t for t in codes)
    assert any("Top supplier" in t for t in codes)
    assert any("variable-rate" in t for t in codes)
    assert any("exchange" in t for t in codes)
    for risk in scan_risk_signals(_full_snapshot(), source="t"):
        assert risk.evidence_refs == ["t"]
        assert risk.estimated_eur is not None


def test_shared_policy_controls_adapter_and_signal_concentration():
    strict = FinancePolicyConfig(concentration_share=0.80)
    risks = scan_risk_signals(_full_snapshot(), policy=strict)
    assert not any("Top customer" in r.title for r in risks)
    assert not any("Top supplier" in r.title for r in risks)

    rows = [
        ArCustomerBalance(customer_id="A", balance_eur=400, days_overdue=0),
        ArCustomerBalance(customer_id="B", balance_eur=300, days_overdue=0),
        ArCustomerBalance(customer_id="C", balance_eur=300, days_overdue=0),
    ]
    default_summary, _ = summarize_ar_aging(rows)
    strict_summary, _ = summarize_ar_aging(rows, policy=strict)
    assert default_summary.concentration_flag is True
    assert strict_summary.concentration_flag is False


def test_opportunity_scan_values_and_overlap_groups():
    opps = {
        o.title: o
        for o in scan_opportunity_signals(_full_snapshot(), source="t")
    }
    assert abs(opps["Release cash by reducing DSO"].estimated_eur - 1_800_000) < 100
    assert (
        opps["Release working capital from excess inventory"].estimated_eur
        == 1_000_000
    )
    assert opps["Recover aged receivables"].estimated_eur == 250_000
    gap = opps["Close the gross-margin gap"].estimated_eur
    assert abs(gap - 93_857_142.0 * 0.03) < 1.0
    assert opps["Procurement savings envelope"].estimated_eur == 1_100_000
    assert (
        opps["Release cash by reducing DSO"].overlap_group
        == opps["Recover aged receivables"].overlap_group
    )
    assert (
        opps["Close the gross-margin gap"].overlap_group
        == opps["Procurement savings envelope"].overlap_group
    )


def test_opportunity_portfolio_prevents_double_counting():
    opportunities = scan_opportunity_signals(_full_snapshot(), source="t")
    portfolio = summarize_opportunities(opportunities)

    assert portfolio.gross_estimated_eur > portfolio.conservative_estimated_eur
    assert set(portfolio.overlap_groups) == {
        "receivables_cash",
        "margin_improvement",
    }

    expected = 1_800_000 + 1_000_000 + (93_857_142.0 * 0.03)
    assert abs(portfolio.conservative_estimated_eur - expected) < 100


def test_quiet_snapshot_stays_quiet():
    snap = CompanySnapshot(
        entity="Q",
        period="2026-09",
        cash=1_000_000.0,
        minimum_cash_buffer=500_000.0,
        receivables_total=1_000_000.0,
        receivables_over_90=0.0,
        top_customer_receivables=100_000.0,
        supplier_spend_total=10_000_000.0,
        top_supplier_spend=1_000_000.0,
    )
    assert scan_risk_signals(snap) == []
    assert scan_opportunity_signals(snap) == []
    assert check_snapshot_consistency(snap) == []


def test_consistency_gates_catch_impossible_inputs():
    snap = CompanySnapshot(
        entity=" ",
        period="2026-09",
        receivables_total=100.0,
        receivables_over_90=200.0,
        variable_rate_debt_share=1.5,
        gross_margin_actual=2.0,
    )
    codes = {f.code for f in check_snapshot_consistency(snap)}
    assert {
        "MISSING_ENTITY",
        "AR_AGING_INCONSISTENT",
        "INVALID_VARIABLE_RATE_SHARE",
        "INVALID_MARGIN",
    } <= codes


def test_markdown_formatter_renders_deduplicated_envelope():
    from enterprise_finance_agent.models import (
        CfoPack,
        RiskFindingDetail,
        RiskLevel,
        ScenarioOutput,
    )

    pack = CfoPack(
        period="2026-09",
        headline_variance_eur=-1_200_000.0,
        root_causes=["hammadde -420k"],
        risks=[
            RiskFindingDetail(
                title="90+ 640k",
                category="collection",
                severity=RiskLevel.HIGH,
                estimated_eur=640_000.0,
            )
        ],
        opportunities=scan_opportunity_signals(_full_snapshot(), source="t"),
        scenarios=[ScenarioOutput(name="FX +5%", ebitda_impact_eur=200_000.0)],
        recommended_actions=["tahsilat sprinti"],
    )
    md = format_cfo_pack_markdown(pack)
    assert "# CFO Finance Pack" in md
    assert "-1,200,000" in md
    assert "Conservative de-duplicated envelope" in md
    assert "receivables_cash" in md
    assert "tahsilat sprinti" in md
