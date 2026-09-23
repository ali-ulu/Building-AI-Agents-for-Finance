"""Governed orchestration boundary.

This module intentionally keeps workflow governance separate from the
agent framework. Specialist agents and data adapters can change without
changing the execution policy contract.

Order per run: authorize (caller-side) -> policy -> workflow ->
validation appends -> exactly one audit event (if a sink is given).
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

from .models import FinanceRequest, FinanceResult, ValidationFinding, RiskLevel
from .policy import evaluate_execution_policy

if TYPE_CHECKING:
    from .audit import AuditSink

FinanceWorkflow = Callable[[FinanceRequest], Awaitable[FinanceResult]]


async def run_governed(
    request: FinanceRequest,
    workflow: FinanceWorkflow,
    *,
    user_id: str = "unknown",
    authorized: bool = True,
    auth_reason: str = "auth not enforced by caller",
    sink: AuditSink | None = None,
    run_id: str | None = None,
) -> FinanceResult:
    """Run a finance workflow only after deterministic policy evaluation.

    Auth/audit are optional and additive: callers that pass
    `authorized=False` get a deterministic denial; callers that pass a
    sink get exactly one audit event per run. Existing callers without
    these args behave exactly as before.
    """

    from .audit import AuditEvent, fingerprint_result

    def _audit(result: FinanceResult, ok: bool) -> None:
        if sink is None:
            return
        sink.append(
            AuditEvent(
                run_id=run_id or request.request_id,
                request_id=request.request_id,
                user_id=user_id,
                action_class=request.action_class.value,
                authorized=ok,
                evidence_count=len(result.evidence),
                finding_codes=[f.code for f in result.findings],
                requires_human_approval=result.requires_human_approval,
                output_fingerprint=fingerprint_result(result),
            )
        )

    if not authorized:
        denied = FinanceResult(
            request_id=request.request_id,
            summary="Execution blocked by authorization.",
            findings=[
                ValidationFinding(
                    code="AUTH_DENIED",
                    severity=RiskLevel.CRITICAL,
                    message=auth_reason,
                )
            ],
            requires_human_approval=True,
        )
        _audit(denied, False)
        return denied

    decision = evaluate_execution_policy(request)

    if not decision.allowed:
        blocked = FinanceResult(
            request_id=request.request_id,
            summary="Execution blocked by finance policy.",
            findings=[
                ValidationFinding(
                    code="EXECUTION_BLOCKED",
                    severity=RiskLevel.CRITICAL,
                    message=decision.reason,
                )
            ],
            requires_human_approval=True,
        )
        _audit(blocked, True)
        return blocked

    result = await workflow(request)

    if decision.requires_human_approval:
        result.requires_human_approval = True
        result.findings.append(
            ValidationFinding(
                code="HUMAN_REVIEW_REQUIRED",
                severity=RiskLevel.HIGH,
                message=decision.reason,
            )
        )

    if not result.evidence:
        result.findings.append(
            ValidationFinding(
                code="NO_EVIDENCE",
                severity=RiskLevel.HIGH,
                message=(
                    "No traceable evidence was attached to the result; "
                    "do not treat it as a finance-grade answer."
                ),
            )
        )

    _audit(result, True)
    return result
