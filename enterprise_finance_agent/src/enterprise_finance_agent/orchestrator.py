"""Governed orchestration boundary.

This module intentionally keeps workflow governance separate from the
agent framework. Specialist agents and data adapters can change without
changing the execution policy contract.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from .models import FinanceRequest, FinanceResult, ValidationFinding, RiskLevel
from .policy import evaluate_execution_policy

FinanceWorkflow = Callable[[FinanceRequest], Awaitable[FinanceResult]]


async def run_governed(
    request: FinanceRequest,
    workflow: FinanceWorkflow,
) -> FinanceResult:
    """Run a finance workflow only after deterministic policy evaluation."""

    decision = evaluate_execution_policy(request)

    if not decision.allowed:
        return FinanceResult(
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

    return result
