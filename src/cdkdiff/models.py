from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum


class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

    def __lt__(self, other: RiskLevel) -> bool:
        return _RISK_ORDER.index(self) < _RISK_ORDER.index(other)

    def __le__(self, other: RiskLevel) -> bool:
        return _RISK_ORDER.index(self) <= _RISK_ORDER.index(other)

    def __gt__(self, other: RiskLevel) -> bool:
        return _RISK_ORDER.index(self) > _RISK_ORDER.index(other)

    def __ge__(self, other: RiskLevel) -> bool:
        return _RISK_ORDER.index(self) >= _RISK_ORDER.index(other)


_RISK_ORDER = [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH]

RISK_EMOJI: dict[RiskLevel, str] = {
    RiskLevel.HIGH: "🔴",
    RiskLevel.MEDIUM: "🟡",
    RiskLevel.LOW: "🟢",
}


class ChangeType(Enum):
    ADD = "add"
    REMOVE = "remove"
    UPDATE = "update"


@dataclass
class Change:
    resource_type: str
    logical_id: str
    change_type: ChangeType
    risk: RiskLevel
    details: str = ""
    requires_replacement: bool = False


@dataclass
class StackDiff:
    name: str
    changes: list[Change] = field(default_factory=list)

    @property
    def risk(self) -> RiskLevel | None:
        if not self.changes:
            return None
        return max((c.risk for c in self.changes), key=lambda r: _RISK_ORDER.index(r))


@dataclass
class DiffSummary:
    stacks: list[StackDiff] = field(default_factory=list)

    @property
    def total_changes(self) -> int:
        return sum(len(s.changes) for s in self.stacks)

    @property
    def highest_risk(self) -> RiskLevel | None:
        risks = [s.risk for s in self.stacks if s.risk is not None]
        if not risks:
            return None
        return max(risks, key=lambda r: _RISK_ORDER.index(r))
