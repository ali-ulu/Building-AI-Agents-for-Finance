"""Auth/RBAC skeleton (additive).

The model never decides access. `authorize()` runs BEFORE `run_governed()`
and only checks identity scope: role minimums + legal-entity scoping.
No IdP integration yet — `User` is built by the host app after SSO.
SSO/row-filtering/PII rules plug in here without touching policy.py.
"""

from __future__ import annotations

from enum import StrEnum

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


_READ_ROLES = {Role.ANALYST, Role.CONTROLLER, Role.CFO, Role.AUDITOR, Role.ADMIN}
_DRAFT_ROLES = {Role.CONTROLLER, Role.CFO, Role.ADMIN}


def authorize(request: FinanceRequest, user: User) -> AuthorizationDecision:
    """Scope check only. Returns deny with reason; never raises."""
    if request.action_class == ActionClass.READ:
        if not _READ_ROLES.intersection(user.roles):
            return AuthorizationDecision(
                allowed=False, reason=f"Role(s) {user.roles} may not run READ."
            )
    elif request.action_class == ActionClass.DRAFT:
        if not _DRAFT_ROLES.intersection(user.roles):
            return AuthorizationDecision(
                allowed=False,
                reason="DRAFT requires controller, cfo or admin role.",
            )
    else:
        # Writes are denied downstream by policy.py; auth denies early too.
        return AuthorizationDecision(
            allowed=False,
            reason=f"{request.action_class} is not permitted in this release.",
        )

    if request.entities:
        out_of_scope = [e for e in request.entities if e not in user.entities]
        if out_of_scope:
            return AuthorizationDecision(
                allowed=False,
                reason=f"Entities out of scope for {user.user_id}: {out_of_scope}.",
            )
    if not user.entities and request.entities:
        return AuthorizationDecision(
            allowed=False, reason=f"User {user.user_id} has no entity scope."
        )
    return AuthorizationDecision(
        allowed=True,
        reason=f"Authorized {user.user_id} for {request.action_class}.",
    )
