"""CFO-facing management pack formatting."""

from __future__ import annotations

from .management_analysis import ManagementAnalysis


def format_cfo_pack(analysis: ManagementAnalysis) -> str:
    """Render a concise management pack from validated deterministic outputs."""

    lines = [
        f"# CFO Finance Pack — {analysis.entity}",
        "",
        f"**Period:** {analysis.period}",
        f"**Currency:** {analysis.currency}",
        f"**Validation:** {'PASS' if analysis.is_valid else 'REVIEW REQUIRED'}",
        "",
        "## Top variance drivers",
        "",
    ]

    for driver in analysis.variance_drivers[:5]:
        direction = "unfavorable" if driver.unfavorable_impact > 0 else "favorable"
        lines.append(
            f"- {driver.name}: actual {driver.actual:,.0f}, budget "
            f"{driver.budget:,.0f}, variance {driver.variance:+,.0f} "
            f"({direction})"
        )

    lines.extend(["", "## Risk scan", ""])
    if analysis.risks:
        for risk in analysis.risks:
            lines.append(
                f"- [{risk.level.upper()}] {risk.title}: {risk.evidence}"
            )
    else:
        lines.append("- No configured deterministic risk threshold breached.")

    lines.extend(["", "## Opportunity scan", ""])
    if analysis.opportunities:
        for opportunity in analysis.opportunities:
            value = (
                f" Estimated value: {opportunity.estimated_value:,.0f} "
                f"{analysis.currency}."
                if opportunity.estimated_value is not None
                else ""
            )
            lines.append(
                f"- {opportunity.title}: {opportunity.rationale}{value}"
            )
    else:
        lines.append("- No configured deterministic opportunity detected.")

    lines.extend(["", "## Scenario sensitivities", ""])
    if analysis.scenarios:
        for scenario in analysis.scenarios:
            lines.append(
                f"- {scenario.name}: {scenario.change_pct:+.1%} change -> "
                f"estimated P&L impact "
                f"{scenario.estimated_pnl_impact:+,.0f} {analysis.currency}"
            )
    else:
        lines.append("- No scenarios supplied.")

    lines.extend(["", "## Validation findings", ""])
    for finding in analysis.findings:
        lines.append(
            f"- [{finding.severity.upper()}] {finding.code}: {finding.message}"
        )

    return "\n".join(lines)
