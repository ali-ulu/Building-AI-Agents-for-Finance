"""Finance-owned deterministic thresholds.

Keep reviewed policy values in one place so adapters, signals and tests do not
silently drift apart.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class FinancePolicyConfig(BaseModel):
    ar_high_share: float = Field(default=0.20, ge=0, le=1)
    ar_elevated_share: float = Field(default=0.10, ge=0, le=1)
    concentration_share: float = Field(default=0.35, ge=0, le=1)
    variable_rate_share: float = Field(default=0.50, ge=0, le=1)


DEFAULT_FINANCE_POLICY = FinancePolicyConfig()
