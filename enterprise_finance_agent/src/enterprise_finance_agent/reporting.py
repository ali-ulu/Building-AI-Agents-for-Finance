"""CFO pack markdown formatter.

Renders validated deterministic outputs. Opportunity totals are reported as
both gross and conservative de-duplicated envelopes to prevent double counting.
"""

from __future__ import annotations

from .models import CfoPack
from .opportunities import summarize_opportunities


def format_cfo_pack_markdown(pack: CfoPack) -> str:
    """Render a concise management pack from a validated CfoPack."""
    lines = [
        f"# CFO Finance Pack — {pack.entity or 'Group'}",
        "",
        f"**Period:** {pack.period}",
        f"**Currency:** {pack.currency}",
        f"**Headline variance:** {pack.headline_variance_eur:+,.0f}",
        "",
        "## Root causes",
        "",
    ]
    for cause in pack.root_causes or ["(none supplied)"]:
        lines.append(f"- {cause}")

    lines.extend(["", "## Risk scan", ""])
    for risk in pack.risks or []:
        eur = (
            f" (~{risk.estimated_eur:,.0f})"
            if risk.estimated_eur is not None
            else ""
        )
        lines.append(f"- [{risk.severity.upper()}] {risk.title}{eur}")
    if not pack.risks:
        lines.append("- No risk findings.")

    lines.extend(["", "## Opportunity scan", ""])
    for opp in pack.opportunities or []:
        overlap = f" | overlap={opp.overlap_group}" if opp.overlap_group else ""
        lines.append(
            f"- {opp.title}: +{opp.estimated_eur:,.0f} "
            f"{pack.currency} [{opp.confidence}]{overlap}"
        )
    if not pack.opportunities:
        lines.append("- No opportunities.")
    else:
        portfolio = summarize_opportunities(pack.opportunities)
        lines.append("")
        lines.append(
            f"**Gross opportunity envelope:** "
            f"{portfolio.gross_estimated_eur:,.0f} {pack.currency}"
        )
        lines.append(
            f"**Conservative de-duplicated envelope:** "
            f"{portfolio.conservative_estimated_eur:,.0f} {pack.currency}"
        )
        if portfolio.overlap_groups:
            lines.append(
                "**Overlap groups:** "
                + ", ".join(sorted(portfolio.overlap_groups))
            )

    lines.extend(["", "## Scenarios", ""])
    for scenario in pack.scenarios or []:
        lines.append(
            f"- {scenario.name}: EBITDA {scenario.ebitda_impact_eur:+,.0f}"
        )
    if not pack.scenarios:
        lines.append("- No scenarios.")

    if pack.debate:
        lines.extend(["", "## Debate (opportunity vs risk)", ""])
        for round_ in pack.debate:
            flag = "ESCALATE" if round_.escalate_to_cfo else "range"
            lines.append(f"- {round_.opportunity_claim}")
            lines.append(f"  vs {round_.risk_rebuttal} -> {flag}")

    lines.extend(["", "## Recommended actions", ""])
    for action in pack.recommended_actions or ["(none)"]:
        lines.append(f"- {action}")

    return "\n".join(lines)
