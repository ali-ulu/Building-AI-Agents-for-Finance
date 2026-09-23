"""Read-only data adapters (CSV-first).

Phase 1 rule: adapters READ sample/real files and return typed summaries.
They never write, never hold credentials, never invent missing rows.
ERP/bank connectors come later; they will target these same return types.
"""

from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field

from .calculators import VarianceLine, build_variance_bridge
from .models import Evidence


class ArCustomerBalance(BaseModel):
    customer_id: str
    balance_eur: float = Field(ge=0)
    days_overdue: int = Field(ge=0)


class ArAgingSummary(BaseModel):
    total_eur: float
    overdue_90plus_eur: float
    top2_share_pct: float
    top2_ids: list[str]
    customer_count: int
    concentration_flag: bool


def summarize_ar_aging(
    rows: list[ArCustomerBalance],
    source: str = "ar_adapter",
    period: str | None = None,
) -> tuple[ArAgingSummary, list[Evidence]]:
    """Summarize AR aging + emit traceable evidence. Pure function."""
    total = sum(r.balance_eur for r in rows)
    overdue = sum(r.balance_eur for r in rows if r.days_overdue >= 90)
    ranked = sorted(rows, key=lambda r: r.balance_eur, reverse=True)
    top2 = ranked[:2]
    top2_sum = sum(r.balance_eur for r in top2)
    share = (top2_sum / total * 100.0) if total > 0 else 0.0
    now = datetime.now(timezone.utc)
    summary = ArAgingSummary(
        total_eur=total,
        overdue_90plus_eur=overdue,
        top2_share_pct=round(share, 1),
        top2_ids=[r.customer_id for r in top2],
        customer_count=len(rows),
        concentration_flag=share > 30.0,
    )
    evidence = [
        Evidence(
            source_system=source,
            as_of=now,
            period=period,
            currency="EUR",
            unit="money",
            value=summary.model_dump(),
        )
    ]
    return summary, evidence


def load_ar_aging_csv(path: str | Path, period: str | None = None) -> tuple[ArAgingSummary, list[Evidence]]:
    """Read columns: customer_id, balance_eur, days_overdue. Read-only."""
    rows: list[ArCustomerBalance] = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        for rec in csv.DictReader(f):
            rows.append(
                ArCustomerBalance(
                    customer_id=rec["customer_id"].strip(),
                    balance_eur=float(rec["balance_eur"]),
                    days_overdue=int(rec["days_overdue"]),
                )
            )
    return summarize_ar_aging(rows, source=f"csv:{Path(path).name}", period=period)


class BudgetActualRow(BaseModel):
    label: str
    budget_eur: float
    actual_eur: float


def load_budget_actual_csv(path: str | Path, period: str | None = None):
    """Read columns: label, budget_eur, actual_eur -> VarianceBridge + Evidence."""
    lines: list[VarianceLine] = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        for rec in csv.DictReader(f):
            lines.append(
                VarianceLine(
                    label=rec["label"].strip(),
                    budget=float(rec["budget_eur"]),
                    actual=float(rec["actual_eur"]),
                )
            )
    bridge = build_variance_bridge(lines)
    evidence = [
        Evidence(
            source_system=f"csv:{Path(path).name}",
            as_of=datetime.now(timezone.utc),
            period=period,
            currency="EUR",
            unit="money",
            value=bridge.model_dump(),
        )
    ]
    return bridge, evidence
