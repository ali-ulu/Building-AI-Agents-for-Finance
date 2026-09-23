"""Runnable deterministic example of the first enterprise workflow."""

from enterprise_finance_agent.cfo_pack import format_cfo_pack
from enterprise_finance_agent.management_analysis import (
    FinanceSnapshot,
    PLLine,
    ScenarioAssumption,
    analyze_management_finance,
)


snapshot = FinanceSnapshot(
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

analysis = analyze_management_finance(
    snapshot,
    scenarios=[
        ScenarioAssumption(
            name="EURUSD adverse move",
            change_pct=-0.05,
            exposure=2_000_000,
        ),
        ScenarioAssumption(
            name="Variable debt rate +100 bps",
            change_pct=-0.01,
            exposure=6_000_000,
        ),
    ],
)

print(format_cfo_pack(analysis))
