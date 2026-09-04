"""Typed reviewer decisions and strict session serialization."""
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping


class DecisionType(str, Enum):
    ACCEPTED = "accepted"
    EXCEPTION = "exception"


@dataclass(frozen=True)
class ReviewDecision:
    check_id: int
    decision: DecisionType
    justification: str | None = None

    @classmethod
    def create(cls, check_id: int, decision: object,
               justification: object = "") -> "ReviewDecision":
        if type(check_id) is not int:
            raise ValueError("Field check_id must be an integer")
        try:
            kind = DecisionType(decision)
        except (TypeError, ValueError) as error:
            raise ValueError("Field decision must be 'accepted' or 'exception'") from error
        if not isinstance(justification, str):
            raise ValueError("Field justification must be a string")
        text = justification.strip()
        if kind is DecisionType.EXCEPTION and len(text) < 10:
            raise ValueError("Justification must be at least 10 characters for an exception")
        if len(text) > 1000:
            raise ValueError("Justification must not exceed 1000 characters")
        return cls(check_id, kind, text if kind is DecisionType.EXCEPTION else None)

    def to_session(self) -> dict[str, str]:
        value = {"decision": self.decision.value}
        if self.justification is not None:
            value["justification"] = self.justification
        return value


def normalize_decisions(raw: object, baseline_ids: set[int], *, strict: bool = False
                        ) -> dict[int, ReviewDecision]:
    """Normalize serialized decisions and optionally reject corrupt active entries."""
    if not isinstance(raw, Mapping):
        if strict:
            raise ValueError("Review state must be a mapping")
        return {}
    normalized: dict[int, ReviewDecision] = {}
    for raw_id, value in raw.items():
        if type(raw_id) is int:
            check_id = raw_id
        elif isinstance(raw_id, str) and raw_id.lstrip('-').isdigit():
            check_id = int(raw_id)
        else:
            if strict:
                raise ValueError(f"Invalid decision check ID: {raw_id!r}")
            continue
        if check_id not in baseline_ids:
            continue
        if strict and check_id in normalized:
            raise ValueError(f"Duplicate review state for check {check_id}")
        if not isinstance(value, Mapping):
            if strict:
                raise ValueError(f"Invalid review state for check {check_id}")
            continue
        try:
            normalized[check_id] = ReviewDecision.create(
                check_id, value.get("decision"), value.get("justification", ""))
        except ValueError:
            if strict:
                raise
    return normalized
