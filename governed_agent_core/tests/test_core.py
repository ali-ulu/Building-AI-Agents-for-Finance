"""Core chassis tests: no domain imports allowed here."""

import asyncio
import json

import governed_agent_core as core
from governed_agent_core import (
    ActionClass,
    AuditEvent,
    JsonlAuditSink,
    MemoryAuditSink,
    Principal,
    RiskLevel,
    Stake,
    Challenge,
    authorize,
    debate_round,
    evaluate_execution_policy,
    fingerprint_mapping,
    run_governed,
    verify_jsonl_audit_chain,
)


def test_policy_blocks_state_changes():
    for action in (
        ActionClass.CONTROLLED_WRITE,
        ActionClass.HIGH_STAKES,
        ActionClass.PRIVILEGED_CHANGE,
    ):
        d = evaluate_execution_policy(action)
        assert d.allowed is False
        assert d.requires_human_approval is True
    assert evaluate_execution_policy(ActionClass.READ).allowed is True
    d = evaluate_execution_policy(ActionClass.READ, RiskLevel.CRITICAL)
    assert d.requires_human_approval is True


def test_auth_scope():
    p = Principal(principal_id="u", roles=["analyst"], scopes=["DE"])
    assert authorize(
        principal=p, action="read", request_scopes=["DE"],
        read_roles={"analyst"}, draft_roles={"controller"},
    ).allowed is True
    assert authorize(
        principal=p, action="read", request_scopes=["FR"],
        read_roles={"analyst"}, draft_roles={"controller"},
    ).allowed is False
    assert authorize(
        principal=p, action="draft", request_scopes=["DE"],
        read_roles={"analyst"}, draft_roles={"controller"},
    ).allowed is False


def test_debate_escalation_rule():
    out = debate_round(
        Stake(label="up", amount=1_000_000, confidence="medium", refs=["e"]),
        Challenge(label="down", amount=700_000, severity=RiskLevel.HIGH),
    )
    assert out.escalate is True
    assert out.agreed_range == (300_000.0, 1_000_000.0)
    calm = debate_round(
        Stake(label="up", amount=1_800_000, confidence="high", refs=["e"]),
        Challenge(label="down", amount=100_000, severity=RiskLevel.LOW),
    )
    assert calm.escalate is False


def test_fingerprint_stable():
    assert fingerprint_mapping({"b": 1, "a": 2}) == fingerprint_mapping(
        {"a": 2, "b": 1}
    )


def _event(run_id: str) -> AuditEvent:
    return AuditEvent(
        run_id=run_id,
        request_id=run_id,
        principal_id="u",
        action_class="read",
        authorized=True,
        evidence_count=1,
    )


def test_memory_audit_is_hash_chained():
    sink = MemoryAuditSink()
    sink.append(_event("r1"))
    sink.append(_event("r2"))
    assert sink.events[0].event_hash
    assert sink.events[1].previous_hash == sink.events[0].event_hash


def test_jsonl_audit_chain_detects_tampering(tmp_path):
    path = tmp_path / "audit.jsonl"
    sink = JsonlAuditSink(path)
    sink.append(_event("r1"))
    sink.append(_event("r2"))
    assert verify_jsonl_audit_chain(path) is True

    lines = path.read_text(encoding="utf-8").splitlines()
    first = json.loads(lines[0])
    first["principal_id"] = "tampered"
    lines[0] = json.dumps(first)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    assert verify_jsonl_audit_chain(path) is False


class _Req:
    def __init__(self):
        self.request_id = "r1"
        self.action_class = ActionClass.READ
        self.risk_level = RiskLevel.LOW


class _Res:
    def __init__(self, **kw):
        self.request_id = kw.get("request_id", "r1")
        self.summary = kw.get("summary", "")
        self.evidence = kw.get("evidence", [])
        self.findings = kw.get("findings", [])
        self.requires_human_approval = kw.get("requires_human_approval", False)


def _finding(code, severity, message):
    return {"code": code, "severity": severity, "message": message}


async def _wf(request):
    return _Res(request_id=request.request_id, summary="ok", evidence=[1])


def test_orchestrator_end_to_end():
    sink = MemoryAuditSink()
    res = asyncio.run(
        run_governed(
            _Req(), _wf,
            result_factory=_Res,
            finding_factory=_finding,
            principal_id="u",
            sink=sink,
        )
    )
    assert res.summary == "ok"
    assert len(sink.events) == 1
    assert sink.events[0].principal_id == "u"
    assert sink.events[0].event_hash


def test_orchestrator_auth_deny():
    res = asyncio.run(
        run_governed(
            _Req(), _wf,
            result_factory=_Res,
            finding_factory=_finding,
            authorized=False,
            auth_reason="nope",
        )
    )
    assert res.findings[0]["code"] == "AUTH_DENIED"


def test_public_surface_has_no_domain_words():
    assert core.__all__ and all(
        w not in " ".join(core.__all__).lower()
        for w in ("finance", "cfo", "ebitda", "ledger")
    )
