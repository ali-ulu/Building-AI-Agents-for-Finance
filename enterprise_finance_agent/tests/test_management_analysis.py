from enterprise_finance_agent.cfo_pack import format_cfo_pack
from enterprise_finance_agent.management_analysis import (
    FinanceSnapshot,
    PLLine,
    ScenarioAssumption,
    analyze_management_finance,
)
from enterprise_finance_agent.models import RiskLevel


def sample_snapshot() -> FinanceSnapshot:
    return FinanceSnapshot(
        entity="DE01",
        period="2026-08",
        currency="EUR",
        pl_lines=[
            PLLine(name="Revenue", actual=9_500_000, budget=10_000_000, kind="revenue"),
            PLLine(name="Raw materials", actual=4_200_000, budget=3_800_000, kind="cost"),
            PLLine(name="Payroll", actual=2_100_000, budget=2_000_000, kind="cost"),
        ],
        cash=1_200_000,
        minimum_cash_buffer=1_500_000,
        receivables_total=3_000_000,
        receivables_over_90=750_000,
        top_customer_receivables=1_200_000,
        payables_total=2_200_000,
        inventory=2_400_000,
        inventory_target=1_900_000,
        annual_revenue=120_000_000,
        dso_days=52,
        dso_target_days=45,
        fx_exposure=2_000_000,
        interest_bearing_debt=10_000_000,
        variable_rate_debt_share=0.60,
        gross_margin_actual=0.31,
        gross_margin_target=0.34,
        procurement_spend=36_000_000,
        procurement_savings_rate=0.02,
        supplier_spend_total=20_000_000,
        top_supplier_spend=8_000_000,
    )


def test_variance_risk_opportunity_and_scenario_pipeline():
    result = analyze_management_finance(
        sample_snapshot(),
        scenarios=[
            ScenarioAssumption(
                name="EURUSD adverse move",
                change_pct=-0.05,
                exposure=2_000_000,
            )
        ],
    )

    assert result.variance_drivers[0].name == "Revenue"
    assert any(r.code == "LIQUIDITY_BUFFER_BREACH" for r in result.risks)
    assert any(r.code == "CUSTOMER_CONCENTRATION" for r in result.risks)
    assert any(r.code == "SUPPLIER_CONCENTRATION" for r in result.risks)
    assert any(o.code == "DSO_REDUCTION" for o in result.opportunities)
    assert any(o.code == "INVENTORY_RELEASE" for o in result.opportunities)
    assert any(o.code == "GROSS_MARGIN_GAP" for o in result.opportunities)
    assert any(o.code == "PROCUREMENT_SAVINGS" for o in result.opportunities)
    assert result.scenarios[0].estimated_pnl_impact == -100_000


def test_dso_opportunity_value_is_deterministic():
    result = analyze_management_finance(sample_snapshot())
    dso = next(o for o in result.opportunities if o.code == "DSO_REDUCTION")
    assert round(dso.estimated_value, 2) == round(120_000_000 / 365 * 7, 2)


def test_margin_and_procurement_values_are_deterministic():
    result = analyze_management_finance(sample_snapshot())

    margin = next(o for o in result.opportunities if o.code == "GROSS_MARGIN_GAP")
    procurement = next(
        o for o in result.opportunities if o.code == "PROCUREMENT_SAVINGS"
    )

    assert round(margin.estimated_value, 2) == 3_600_000
    assert round(procurement.estimated_value, 2) == 720_000


def test_invalid_receivables_are_rejected():
    snapshot = sample_snapshot()
    snapshot.receivables_over_90 = 4_000_000

    result = analyze_management_finance(snapshot)

    assert result.is_valid is False
    assert any(
        f.code == "AR_AGING_INCONSISTENT"
        and f.severity == RiskLevel.CRITICAL
        for f in result.findings
    )


def test_invalid_supplier_concentration_is_rejected():
    snapshot = sample_snapshot()
    snapshot.top_supplier_spend = 25_000_000

    result = analyze_management_finance(snapshot)

    assert result.is_valid is False
    assert any(
        f.code == "SUPPLIER_CONCENTRATION_INCONSISTENT"
        for f in result.findings
    )


def test_cfo_pack_contains_all_sections():
    result = analyze_management_finance(sample_snapshot())
    report = format_cfo_pack(result)

    assert "Top variance drivers" in report
    assert "Risk scan" in report
    assert "Opportunity scan" in report
    assert "Scenario sensitivities" in report
    assert "Validation findings" in report
