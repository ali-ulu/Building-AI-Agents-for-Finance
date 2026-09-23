"""Deterministic execution policy.

The model may recommend an action class, but this module owns the final
execution decision. Default posture is read/draft only: anything that
changes state is denied until a workflow-specific approval system exists.
"""

from __future__ import annotations

from pydantic import BaseModel

from .actions import ActionClass, RiskLevel


class ExecutionDecision(BaseModel):
    allowed: bool
    requires_human_approval: bool
    reason: str


_ALWAYS_BLOCKED = {
    ActionClass.CONTROLLED_WRITE,
    ActionClass.HIGH_STAKES,
    ActionClass.PRIVILEGED_CHANGE,
}


def evaluate_execution_policy(
    action_class: ActionClass, risk_level: RiskLevel = RiskLevel.LOW
) -> ExecutionDecision:
    """Pure function over action class + risk. No I/O, no model calls."""

    if action_class in _ALWAYS_BLOCKED:
        return ExecutionDecision(
            allowed=False,
            requires_human_approval=True,
            reason=(
                "Default posture is read/draft only; state-changing actions "
                "require a workflow-specific approval system."
            ),
        )

    if action_class == ActionClass.DRAFT:
        return ExecutionDecision(
            allowed=True,
            requires_human_approval=True,
            reason="Drafting is allowed, but the draft cannot execute itself.",
        )

    if risk_level in {RiskLevel.HIGH, RiskLevel.CRITICAL}:
        return ExecutionDecision(
            allowed=True,
            requires_human_approval=True,
            reason="High-risk analysis requires human review before reliance.",
        )

    return ExecutionDecision(
        allowed=True,
        requires_human_approval=False,
        reason="Read-only analysis is permitted.",
    )
