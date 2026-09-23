"""Deterministic policy gate for finance actions.

The model may recommend an action class, but this module owns the final
execution decision. Foundation release is read/draft only.
"""

from __future__ import annotations

from pydantic import BaseModel

from .models import ActionClass, FinanceRequest, RiskLevel


class ExecutionDecision(BaseModel):
    allowed: bool
    requires_human_approval: bool
    reason: str


_ALWAYS_BLOCKED = {
    ActionClass.CONTROLLED_WRITE,
    ActionClass.MONEY_MOVEMENT,
    ActionClass.PRIVILEGED_CHANGE,
}


def evaluate_execution_policy(request: FinanceRequest) -> ExecutionDecision:
    """Apply the foundation release's hard execution policy."""

    if request.action_class in _ALWAYS_BLOCKED:
        return ExecutionDecision(
            allowed=False,
            requires_human_approval=True,
            reason=(
                "Foundation release is read/draft only; state-changing "
                "finance actions require a workflow-specific approval system."
            ),
        )

    if request.action_class == ActionClass.DRAFT:
        return ExecutionDecision(
            allowed=True,
            requires_human_approval=True,
            reason="Drafting is allowed, but the draft cannot execute itself.",
        )

    if request.risk_level in {RiskLevel.HIGH, RiskLevel.CRITICAL}:
        return ExecutionDecision(
            allowed=True,
            requires_human_approval=True,
            reason="High-risk analysis requires human review before reliance.",
        )

    return ExecutionDecision(
        allowed=True,
        requires_human_approval=False,
        reason="Read-only finance analysis is permitted.",
    )
