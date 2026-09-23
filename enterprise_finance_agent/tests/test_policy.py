from enterprise_finance_agent.models import ActionClass, FinanceRequest, RiskLevel
from enterprise_finance_agent.policy import evaluate_execution_policy


def request(action: ActionClass, risk: RiskLevel = RiskLevel.LOW) -> FinanceRequest:
    return FinanceRequest(
        request_id="req-1",
        user_id="user-1",
        intent="test",
        action_class=action,
        risk_level=risk,
    )


def test_read_is_allowed():
    decision = evaluate_execution_policy(request(ActionClass.READ))
    assert decision.allowed is True
    assert decision.requires_human_approval is False


def test_draft_requires_approval():
    decision = evaluate_execution_policy(request(ActionClass.DRAFT))
    assert decision.allowed is True
    assert decision.requires_human_approval is True


def test_money_movement_is_blocked():
    decision = evaluate_execution_policy(request(ActionClass.MONEY_MOVEMENT))
    assert decision.allowed is False
    assert decision.requires_human_approval is True


def test_high_risk_read_requires_review():
    decision = evaluate_execution_policy(
        request(ActionClass.READ, RiskLevel.HIGH)
    )
    assert decision.allowed is True
    assert decision.requires_human_approval is True
