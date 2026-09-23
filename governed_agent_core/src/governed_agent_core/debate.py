"""Adversarial debate engine (domain-free).

One side states a quantified upside (Stake), the other states a quantified
downside (Challenge) over the SAME evidence. The engine never nets numbers
into a fake consensus: if the downside wipes out more than half the upside,
it escalates for human decision and reports the surviving range instead.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from .actions import RiskLevel


class Stake(BaseModel):
    label: str
    amount: float
    confidence: str = Field(description="high | medium | low")
    refs: list[str] = Field(default_factory=list)


class Challenge(BaseModel):
    label: str
    amount: float | None = None
    severity: RiskLevel = RiskLevel.MEDIUM
    refs: list[str] = Field(default_factory=list)
    mitigation: str | None = None


class DebateOutcome(BaseModel):
    claim: str
    rebuttal: str
    agreed_range: tuple[float, float] | None = None
    escalate: bool = False


def debate_round(stake: Stake, challenge: Challenge) -> DebateOutcome:
    """Single claim-vs-rebuttal round with an explicit escalation rule."""
    upside = stake.amount
    downside = challenge.amount if challenge.amount is not None else 0.0
    escalate = downside > 0.5 * upside if upside > 0 else challenge.severity in {
        RiskLevel.HIGH,
        RiskLevel.CRITICAL,
    }
    low = max(0.0, upside - downside)
    return DebateOutcome(
        claim=f"{stake.label}: +{upside:,.0f} ({stake.confidence})",
        rebuttal=f"{challenge.label}: -{downside:,.0f} [{challenge.severity}]",
        agreed_range=(low, upside),
        escalate=escalate,
    )
