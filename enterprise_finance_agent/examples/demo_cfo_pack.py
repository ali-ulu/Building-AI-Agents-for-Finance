"""V1 demo: aylik kapanis CFO pack'i (kullanicinin sayilariyla)."""

from enterprise_finance_agent.calculators import (
    FxExposure,
    VarianceLine,
    build_variance_bridge,
    cash_release_for_dso_reduction,
    fx_ebitda_impact,
    working_capital_metrics,
    WorkingCapitalInput,
)
from enterprise_finance_agent.debate import debate_round, validate_cfo_pack
from enterprise_finance_agent.models import (
    CfoPack,
    OpportunityFinding,
    RiskFindingDetail,
    RiskLevel,
    ScenarioOutput,
)

# 1. Actual vs Budget + Root Cause (deterministik bridge)
bridge = build_variance_bridge(
    [
        VarianceLine(label="hammadde", budget=0.0, actual=-420_000.0),
        VarianceLine(label="satis hacmi", budget=0.0, actual=-510_000.0),
        VarianceLine(label="FX", budget=0.0, actual=-180_000.0),
        VarianceLine(label="diger (aciklanmayan)", budget=0.0, actual=-90_000.0),
    ]
)

# 2. Working Capital: DSO 52 -> 45 gunde ~1.8M EUR nakit
annual_revenue = 1_800_000.0 / 7.0 * 365.0  # ~93.86M
cash_freed = cash_release_for_dso_reduction(annual_revenue, 52, 45)
wc = working_capital_metrics(
    WorkingCapitalInput(
        annual_revenue=annual_revenue,
        annual_cogs=60_000_000.0,
        annual_purchases=55_000_000.0,
        receivables=annual_revenue / 365.0 * 52,
        inventory=8_219_178.0,
        payables=7_534_246.0,
    )
)

# 3. Scenario: EUR/USD %5 -> yaklasik X (varsayim acik)
fx_impact = fx_ebitda_impact(
    FxExposure(net_foreign_currency_exposure=4_000_000.0, base_rate=1.08), 5.0
)

# 4. Opportunity vs Risk (bagimsiz) + debate
opp = OpportunityFinding(
    title="DSO 52->45 ile nakit serbest birakma",
    category="cash",
    estimated_eur=round(cash_freed),
    confidence="high",
    assumptions=["Yillik ciro ~93.9M EUR sabit", "Tahsilat kosullari musteri kaybi olmadan sikilastirilir"],
    evidence_refs=["AR_adapter:2026-09", "working_capital_metrics:dso=52"],
)
risk = RiskFindingDetail(
    title="2 musteride alacak konsantrasyonu, 90+ gun 640k EUR",
    category="collection",
    severity=RiskLevel.HIGH,
    estimated_eur=640_000.0,
    evidence_refs=["AR_aging:2026-09"],
    mitigation_hint="Top-2 hesaba haftalik tahsilat sprinti + kredi limit gozden gecirme.",
)
plant_opp = OpportunityFinding(
    title="Yeni tesis marj artisi",
    category="margin",
    estimated_eur=1_000_000.0,
    confidence="medium",
    assumptions=["Kapasite kullanimi %85+"],
    evidence_refs=["capex_model:v3"],
)
plant_risk = RiskFindingDetail(
    title="Talep %15 duserse IRR %14->%6",
    category="ops",
    severity=RiskLevel.HIGH,
    estimated_eur=700_000.0,
    evidence_refs=["scenario:demand-15pct"],
    mitigation_hint="Fazli yatirim, moduler kapasite ile kademelendir.",
)

pack = CfoPack(
    period="2026-09",
    entity="Group",
    currency="EUR",
    headline_variance_eur=bridge.total_variance,
    root_causes=[
        "hammadde -420k EUR",
        "satis hacmi -510k EUR",
        "FX -180k EUR",
        "diger/aciklanmayan -90k EUR",
    ],
    risks=[risk, plant_risk],
    opportunities=[opp, plant_opp],
    scenarios=[
        ScenarioOutput(
            name="EUR/USD +5%",
            ebitda_impact_eur=fx_impact,
            assumptions=["Net 4.0M USD acik pozisyon, lineer translasyon"],
        ),
        ScenarioOutput(
            name="Satis -8%",
            ebitda_impact_eur=-820_000.0,
            assumptions=["Katki marji %35, sabit maliyet kisa vadede yapiskan"],
        ),
        ScenarioOutput(
            name="Enerji +15%",
            ebitda_impact_eur=-310_000.0,
            assumptions=["Yillik enerji baz ~2.1M EUR"],
        ),
    ],
    debate=[debate_round(opp, risk), debate_round(plant_opp, plant_risk)],
    recommended_actions=[
        "Tahsilat: top-2 musteriye haftalik sprint, 90+ 640k EUR hedefli.",
        "Hedge: 4M USD acik pozisyonun %50'sine 6-ay forward fiyatla.",
        "Satin alma: hammadde +420k icin 2 alternatif tedarikci + 60 gun fiyat sabitleme incelensin.",
    ],
)

findings = validate_cfo_pack(pack)

print("=" * 64)
print(f"CFO PACK  {pack.period}  ({pack.entity}, {pack.currency})")
print("=" * 64)
print(f"\nEBITDA butcenin {abs(pack.headline_variance_eur):,.0f} EUR altinda.")
print(f"Bridge toplami: {bridge.total_variance:,.0f} | aciklanmayan: {bridge.unexplained:,.0f}")
print("\n--- NEDEN ---")
for rc in pack.root_causes:
    print(f"  - {rc}")
print("\n--- RISK ---")
for r in pack.risks:
    eur = f"{r.estimated_eur:,.0f} EUR" if r.estimated_eur else "kantifiye disi"
    print(f"  [{r.severity}] {r.title} ({eur})")
    if r.mitigation_hint:
        print(f"      -> {r.mitigation_hint}")
print("\n--- FIRSAT ---")
for o in pack.opportunities:
    print(f"  +{o.estimated_eur:,.0f} EUR  {o.title} [{o.confidence}]")
print(f"  (DSO muhendisligi: DSO={wc.dso:.1f}, DIO={wc.dio:.1f}, DPO={wc.dpo:.1f}, CCC={wc.ccc:.1f})")
print("\n--- SENARYO ---")
for s in pack.scenarios:
    print(f"  {s.name}: EBITDA etkisi {s.ebitda_impact_eur:+,.0f} EUR")
print("\n--- DEBATE (Opportunity vs Risk) ---")
for d in pack.debate:
    flag = "ESCALATE" if d.escalate_to_cfo else "mutabik aralik"
    lo, hi = d.agreed_eur_range or (0, 0)
    print(f"  iddia: {d.opportunity_claim}")
    print(f"  rebuttal: {d.risk_rebuttal}")
    print(f"  -> {flag}: {lo:,.0f}..{hi:,.0f} EUR")
print("\n--- AKSIYON ---")
for a in pack.recommended_actions:
    print(f"  * {a}")
print("\n--- VALIDATOR ---")
if not findings:
    print("  temiz: tum deterministik kapilar gecti.")
else:
    for f in findings:
        print(f"  [{f.severity}] {f.code}: {f.message}")
