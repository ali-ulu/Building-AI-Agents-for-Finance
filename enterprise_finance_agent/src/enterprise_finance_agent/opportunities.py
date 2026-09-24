"""Opportunity aggregation without double counting.

Signals may deliberately describe the same economic value from different
angles. CFO reporting must not add overlapping envelopes as if each were
independently realizable.
"""

from __future__ import annotations

from collections import defaultdict

from .models import OpportunityFinding, OpportunityPortfolio


def summarize_opportunities(
    opportunities: list[OpportunityFinding],
) -> OpportunityPortfolio:
    """Return gross and conservative de-duplicated opportunity envelopes.

    Opportunities sharing an overlap_group are treated as alternative or
    nested views of the same underlying value. The conservative envelope uses
    only the largest estimate in each overlap group. Opportunities without an
    overlap group remain independently additive.
    """
    gross = sum(max(0.0, item.estimated_eur) for item in opportunities)

    grouped: dict[str, list[OpportunityFinding]] = defaultdict(list)
    independent: list[OpportunityFinding] = []
    for item in opportunities:
        if item.overlap_group:
            grouped[item.overlap_group].append(item)
        else:
            independent.append(item)

    conservative = sum(max(0.0, item.estimated_eur) for item in independent)
    overlaps: dict[str, list[str]] = {}

    for group, items in grouped.items():
        conservative += max(max(0.0, item.estimated_eur) for item in items)
        if len(items) > 1:
            overlaps[group] = [item.title for item in items]

    return OpportunityPortfolio(
        gross_estimated_eur=gross,
        conservative_estimated_eur=conservative,
        overlap_groups=overlaps,
    )
