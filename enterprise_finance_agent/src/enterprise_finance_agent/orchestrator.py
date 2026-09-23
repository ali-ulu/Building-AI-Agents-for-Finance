"""Governed orchestration boundary (finance adapter).

Execution order and audit semantics live in governed_agent_core; this
module only plugs finance types (FinanceRequest/FinanceResult/
ValidationFinding) into the generic engine.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from governed_agent_core.orchestrator import run_governed as _run_governed

from .audit import AuditSink
from .models import FinanceRequest, FinanceResult, RiskLevel, ValidationFinding

FinanceWorkflow = Callable[[FinanceRequest], Awaitable[FinanceResult]]


def _result_factory(**kwargs) -> FinanceResult:
    return FinanceResult(**kwargs)


def _finding_factory(code: str, severity: RiskLevel, message: str):
    return ValidationFinding(code=code, severity=severity, message=message)


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
    """Run a finance workflow only after deterministic policy evaluation."""
    return await _run_governed(
        request,
        workflow,  # type: ignore[arg-type]
        result_factory=_result_factory,
        finding_factory=_finding_factory,
        principal_id=user_id,
        authorized=authorized,
        auth_reason=auth_reason,
        sink=sink,
        run_id=run_id,
    )
