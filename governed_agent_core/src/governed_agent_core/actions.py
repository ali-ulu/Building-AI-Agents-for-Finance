"""Generic action/risk taxonomy. No domain words here on purpose."""

from __future__ import annotations

from enum import StrEnum


class ActionClass(StrEnum):
    READ = "read"
    DRAFT = "draft"
    CONTROLLED_WRITE = "controlled_write"
    HIGH_STAKES = "high_stakes"
    PRIVILEGED_CHANGE = "privileged_change"


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
