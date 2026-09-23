"""Golden regression gate: eval/golden_cases.json drives deterministic checks.

Add a case here when finance reviews a new scenario. If a golden case
fails, the calculators/contracts changed — investigate, don't edit the
expected value to make it green without finance sign-off.
"""

import json
from pathlib import Path

from enterprise_finance_agent.adapters import (
    ArCustomerBalance,
    summarize_ar_aging,
)
from enterprise_finance_agent.auth import Role, User, authorize
from enterprise_finance_agent.calculators import (
    VarianceLine,
    cash_release_for_dso_reduction,
    fx_ebitda_impact,
    FxExposure,
    build_variance_bridge,
)
from enterprise_finance_agent.debate import debate_round, validate_cfo_pack
from enterprise_finance_agent.models import (
    ActionClass,
    CfoPack,
    FinanceRequest,
    OpportunityFinding,
    RiskFindingDetail,
    RiskLevel,
    ScenarioOutput,
)

CASES = json.loads(
    (Path(__file__).parent.parent / "eval" / "golden_cases.json").read_text(
        encoding="utf-8"
    )
)


def _clean_pack() -> CfoPack:
    return CfoPack(
        period="2026-09",
        headline_variance_eur=-1_200_000.0,
        root_causes=["hammadde -420k"],
        risks=[
            RiskFindingDetail(
                title="90+ 640k",
                category="collection",
                severity=RiskLevel.HIGH,
                estimated_eur=640_000.0,
                evidence_refs=["ar"],
                mitigation_hint="sprint",
            )
        ],
        opportunities=[
            OpportunityFinding(
                title="DSO 52->45",
                category="cash",
                estimated_eur=1_800_000.0,
                confidence="high",
                evidence_refs=["ar"],
            )
        ],
        scenarios=[ScenarioOutput(name="FX +5%", ebitda_impact_eur=200_000.0)],
        recommended_actions=["tahsilat sprinti"],
    )


def _broken_pack() -> CfoPack:
    return CfoPack(period="2026-09", headline_variance_eur=-1.0)


def _run_case(case: dict):
    run, inputs, expected = case["run"], case["inputs"], case["expected"]
    if run == "variance_bridge":
        b = build_variance_bridge(
            [VarianceLine(label=n, budget=x, actual=y) for n, x, y in inputs["lines"]]
        )
        assert b.total_variance == expected["total_variance"], case["id"]
        assert b.unexplained == expected["unexplained"], case["id"]
    elif run == "dso_release":
        got = cash_release_for_dso_reduction(
            inputs["annual_revenue"], inputs["current_dso"], inputs["target_dso"]
        )
        assert abs(got - expected["cash_freed"]) <= expected["tolerance"], case["id"]
    elif run == "fx_impact":
        got = fx_ebitda_impact(
            FxExposure(
                net_foreign_currency_exposure=inputs["exposure"], base_rate=1.08
            ),
            inputs["move_pct"],
        )
        assert abs(got - expected["impact"]) <= expected["tolerance"], case["id"]
    elif run == "ar_aging":
        summary, _ = summarize_ar_aging(
            [
                ArCustomerBalance(
                    customer_id=c, balance_eur=b, days_overdue=d
                )
                for c, b, d in inputs["rows"]
            ]
        )
        assert summary.total_eur == expected["total"], case["id"]
        assert summary.overdue_90plus_eur == expected["overdue_90plus"], case["id"]
        assert summary.concentration_flag is expected["concentration_flag"], case["id"]
    elif run == "debate":
        opp = OpportunityFinding(
            title="t",
            category="cash",
            estimated_eur=inputs["upside"],
            confidence="medium",
            evidence_refs=["e"],
        )
        risk = RiskFindingDetail(
            title="t",
            category="ops",
            severity=RiskLevel(inputs["severity"]),
            estimated_eur=inputs["downside"],
        )
        d = debate_round(opp, risk)
        assert d.escalate_to_cfo is expected["escalate"], case["id"]
        assert tuple(d.agreed_eur_range or ()) == tuple(expected["range"]), case["id"]
    elif run == "validate_pack":
        pack = _clean_pack() if inputs["pack"] == "clean" else _broken_pack()
        codes = sorted(f.code for f in validate_cfo_pack(pack))
        assert codes == sorted(expected["codes"]), (case["id"], codes)
    elif run == "auth":
        user = User(
            user_id="u1",
            roles=[Role(r) for r in inputs["roles"]],
            entities=inputs["user_entities"],
        )
        req = FinanceRequest(
            request_id="r1",
            user_id="u1",
            intent="t",
            action_class=ActionClass(inputs.get("action", "read")),
            entities=inputs["request_entities"],
        )
        dec = authorize(req, user)
        assert dec.allowed is expected["allowed"], case["id"]
    else:
        raise AssertionError(f"unknown run type: {run}")


def test_golden_cases():
    assert len(CASES) >= 10, "golden set must keep growing, never shrink silently"
    for case in CASES:
        _run_case(case)
