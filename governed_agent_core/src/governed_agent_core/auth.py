"""Scope authorization skeleton (additive).

The model never decides access. `authorize()` checks role minimums per
action plus principal scope coverage. Identity comes from the host app
after SSO; IdP wiring, row-filtering and PII rules plug in here.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class Principal(BaseModel):
    principal_id: str
    roles: list[str] = Field(default_factory=list)
    scopes: list[str] = Field(
        default_factory=list,
        description="Allowed scopes (entities, tenants, ...). Empty = no access.",
    )


class AuthorizationDecision(BaseModel):
    allowed: bool
    reason: str


def authorize(
    *,
    principal: Principal,
    action: str,
    request_scopes: list[str],
    read_roles: set[str],
    draft_roles: set[str],
) -> AuthorizationDecision:
    """Scope check only. Returns deny with reason; never raises."""
    if action == "read":
        if not read_roles.intersection(principal.roles):
            return AuthorizationDecision(
                allowed=False,
                reason=f"Role(s) {principal.roles} may not run read.",
            )
    elif action == "draft":
        if not draft_roles.intersection(principal.roles):
            return AuthorizationDecision(
                allowed=False,
                reason="Draft requires an elevated role.",
            )
    else:
        return AuthorizationDecision(
            allowed=False,
            reason=f"Action '{action}' is not permitted in this release.",
        )

    out_of_scope = [s for s in request_scopes if s not in principal.scopes]
    if out_of_scope:
        return AuthorizationDecision(
            allowed=False,
            reason=f"Scopes out of range for {principal.principal_id}: {out_of_scope}.",
        )
    return AuthorizationDecision(
        allowed=True,
        reason=f"Authorized {principal.principal_id} for {action}.",
    )
