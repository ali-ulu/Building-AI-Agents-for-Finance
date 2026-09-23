"""Adapters + auth + audit + orchestrator wiring."""

import asyncio

from enterprise_finance_agent.adapters import load_ar_aging_csv, load_budget_actual_csv
from enterprise_finance_agent.audit import (
    JsonlAuditSink,
    MemoryAuditSink,
    fingerprint_result,
)
from enterprise_finance_agent.auth import Role, User, authorize
from enterprise_finance_agent.models import (
    ActionClass,
    Evidence,
    FinanceRequest,
    FinanceResult,
)
from enterprise_finance_agent.orchestrator import run_governed


def _req(**kw) -> FinanceRequest:
    base = dict(request_id="r1", user_id="u1", intent="q")
    base.update(kw)
    return FinanceRequest(**base)


def test_ar_csv_loader(tmp_path):
    p = tmp_path / "ar.csv"
    p.write_text(
        "customer_id,balance_eur,days_overdue\nA,500000,95\nB,400000,20\nC,100000,10\n",
        encoding="utf-8",
    )
    summary, evidence = load_ar_aging_csv(p, period="2026-09")
    assert summary.total_eur == 1_000_000
    assert summary.overdue_90plus_eur == 500_000
    assert summary.concentration_flag is True
    assert evidence and evidence[0].period == "2026-09"


def test_budget_csv_loader(tmp_path):
    p = tmp_path / "b.csv"
    p.write_text(
        "label,budget_eur,actual_eur\nhammadde,0,-420000\nfx,0,-180000\n",
        encoding="utf-8",
    )
    bridge, _ = load_budget_actual_csv(p)
    assert bridge.total_variance == -600_000


def test_auth_roles_and_scope():
    analyst = User(user_id="a", roles=[Role.ANALYST], entities=["DE"])
    assert authorize(_req(entities=["DE"]), analyst).allowed is True
    assert authorize(_req(entities=["FR"]), analyst).allowed is False
    draft = _req(action_class=ActionClass.DRAFT, entities=["DE"])
    assert authorize(draft, analyst).allowed is False
    cfo = User(user_id="c", roles=[Role.CFO], entities=["DE"])
    assert authorize(draft, cfo).allowed is True
    assert authorize(
        _req(action_class=ActionClass.HIGH_STAKES), cfo
    ).allowed is False


async def _ok_workflow(request: FinanceRequest) -> FinanceResult:
    from datetime import datetime, timezone

    return FinanceResult(
        request_id=request.request_id,
        summary="ok",
        evidence=[
            Evidence(
                source_system="t",
                as_of=datetime.now(timezone.utc),
                value=1,
            )
        ],
    )


def test_orchestrator_denies_and_audits():
    sink = MemoryAuditSink()
    denied = asyncio.run(
        run_governed(
            _req(),
            _ok_workflow,
            user_id="a",
            authorized=False,
            auth_reason="no scope",
            sink=sink,
        )
    )
    assert [f.code for f in denied.findings] == ["AUTH_DENIED"]
    assert len(sink.events) == 1
    assert sink.events[0].authorized is False


def test_orchestrator_audits_allowed_run():
    sink = MemoryAuditSink()
    result = asyncio.run(
        run_governed(_req(), _ok_workflow, user_id="a", sink=sink, run_id="run-1")
    )
    assert result.summary == "ok"
    assert len(sink.events) == 1
    assert sink.events[0].run_id == "run-1"
    assert sink.events[0].output_fingerprint == fingerprint_result(result)


def test_orchestrator_backward_compatible_no_sink():
    result = asyncio.run(run_governed(_req(), _ok_workflow))
    assert result.summary == "ok"


def test_fingerprint_stable_and_jsonl_roundtrip(tmp_path):
    r = asyncio.run(run_governed(_req(), _ok_workflow))
    assert fingerprint_result(r) == fingerprint_result(r)
    sink = JsonlAuditSink(tmp_path / "audit.jsonl")
    asyncio.run(run_governed(_req(), _ok_workflow, sink=sink))
    line = (tmp_path / "audit.jsonl").read_text(encoding="utf-8").strip()
    assert '"request_id":"r1"' in line.replace(" ", "")
