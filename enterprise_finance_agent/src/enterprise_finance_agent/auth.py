"""Finance scope authorization. Roles stay finance-flavored; the scope
check engine lives in core."""

from __future__ import annotations

from enum import StrEnum

from governed_agent_core.auth import Principal
from governed_agent_core.auth import authorize as _authorize
from pydantic import BaseModel, Field

from .models import ActionClass, FinanceRequest


class Role(StrEnum):
    ANALYST = "analyst"
    CONTROLLER = "controller"
    CFO = "cfo"
    AUDITOR = "auditor"
    ADMIN = "admin"


class User(BaseModel):
    user_id: str
    roles: list[Role] = Field(default_factory=lambda: [Role.ANALYST])
    entities: list[str] = Field(
        default_factory=list,
        description="Legal-entity scope. Empty = no entity access.",
    )


class AuthorizationDecision(BaseModel):
    allowed: bool
    reason: str


_READ_ROLES = {Role.ANALYST.value, Role.CONTROLLER.value, Role.CFO.value,
               Role.AUDITOR.value, Role.ADMIN.value}
_DRAFT_ROLES = {Role.CONTROLLER.value, Role.CFO.value, Role.ADMIN.value}


def authorize(request: FinanceRequest, user: User) -> AuthorizationDecision:
    """Scope check only. Money movement and privileged changes are denied
    here and (belt-and-braces) downstream by policy.py."""
    if request.action_class in {
        ActionClass.CONTROLLED_WRITE,
        ActionClass.HIGH_STAKES,
        ActionClass.PRIVILEGED_CHANGE,
    }:
        return AuthorizationDecision(
            allowed=False,
            reason=f"{request.action_class.value} is not permitted in this release.",
        )
    action = "draft" if request.action_class == ActionClass.DRAFT else "read"
    decision = _authorize(
        principal=Principal(
            principal_id=user.user_id,
            roles=[r.value for r in user.roles],
            scopes=user.entities,
        ),
        action=action,
        request_scopes=request.entities,
        read_roles=_READ_ROLES,
        draft_roles=_DRAFT_ROLES,
    )
    return AuthorizationDecision(
        allowed=decision.allowed, reason=decision.reason
    )
