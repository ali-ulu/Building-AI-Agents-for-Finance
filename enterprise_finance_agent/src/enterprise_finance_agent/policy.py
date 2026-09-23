"""Deterministic policy gate for finance actions.

Thin domain wrapper over governed_agent_core.policy: the money-movement
vocabulary stays here, the blocking rules live in core.
"""

from __future__ import annotations

from governed_agent_core.policy import (
    ExecutionDecision as ExecutionDecision,
    evaluate_execution_policy as _evaluate,
)

from .models import FinanceRequest


def evaluate_execution_policy(request: FinanceRequest) -> ExecutionDecision:
    """Apply the foundation release's hard execution policy."""
    return _evaluate(request.action_class, request.risk_level)
