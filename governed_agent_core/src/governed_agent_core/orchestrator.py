"""Governed orchestration boundary (domain-free).

Order per run: authorize (caller-side) -> policy -> workflow ->
validation appends -> exactly one audit event (if a sink is given).

Requests/results are structural (Protocol): any domain model with the
listed fields works. Denied/blocked/validation findings are built through
caller-supplied factories so this module never imports domain models.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Protocol

from .actions import ActionClass, RiskLevel
from .audit import AuditEvent, AuditSink, fingerprint_mapping
from .policy import evaluate_execution_policy


class GovernedRequest(Protocol):
    request_id: str
    action_class: ActionClass
    risk_level: RiskLevel


class GovernedResult(Protocol):
    request_id: str
    summary: str
    evidence: list
    findings: list
    requires_human_approval: bool


GovernedWorkflow = Callable[[GovernedRequest], Awaitable[GovernedResult]]
ResultFactory = Callable[..., GovernedResult]


async def run_governed(
    request: GovernedRequest,
    workflow: GovernedWorkflow,
    *,
    result_factory: ResultFactory,
    finding_factory: Callable[[str, RiskLevel, str], object],
    principal_id: str = "unknown",
    authorized: bool = True,
    auth_reason: str = "auth not enforced by caller",
    sink: AuditSink | None = None,
    run_id: str | None = None,
) -> GovernedResult:
    """Run a workflow after deterministic policy evaluation.

    `result_factory(request_id=..., summary=..., findings=[...],
    requires_human_approval=...)` builds domain results;
    `finding_factory(code, severity, message)` builds domain findings.
    All other kwargs are optional and additive.
    """

    def _finding(code: str, severity: RiskLevel, message: str):
        return finding_factory(code, severity, message)

    def _audit(result: GovernedResult, ok: bool) -> None:
        if sink is None:
            return
        sink.append(
            AuditEvent(
                run_id=run_id or request.request_id,
                request_id=request.request_id,
                principal_id=principal_id,
                action_class=request.action_class.value,
                authorized=ok,
                evidence_count=len(result.evidence),
                finding_codes=[f.code for f in result.findings],
                requires_human_approval=result.requires_human_approval,
                output_fingerprint=fingerprint_mapping(
                    {
                        "request_id": result.request_id,
                        "summary": result.summary,
                        "findings": sorted(f.code for f in result.findings),
                        "evidence_count": len(result.evidence),
                    }
                ),
            )
        )

    if not authorized:
        denied = result_factory(
            request_id=request.request_id,
            summary="Execution blocked by authorization.",
            findings=[
                _finding("AUTH_DENIED", RiskLevel.CRITICAL, auth_reason)
            ],
            requires_human_approval=True,
        )
        _audit(denied, False)
        return denied

    decision = evaluate_execution_policy(request.action_class, request.risk_level)

    if not decision.allowed:
        blocked = result_factory(
            request_id=request.request_id,
            summary="Execution blocked by policy.",
            findings=[
                _finding("EXECUTION_BLOCKED", RiskLevel.CRITICAL, decision.reason)
            ],
            requires_human_approval=True,
        )
        _audit(blocked, True)
        return blocked

    result = await workflow(request)

    if decision.requires_human_approval:
        result.requires_human_approval = True
        result.findings.append(
            _finding("HUMAN_REVIEW_REQUIRED", RiskLevel.HIGH, decision.reason)
        )

    if not result.evidence:
        result.findings.append(
            _finding(
                "NO_EVIDENCE",
                RiskLevel.HIGH,
                "No traceable evidence was attached to the result; "
                "do not treat it as a production-grade answer.",
            )
        )

    _audit(result, True)
    return result
