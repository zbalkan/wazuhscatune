from dataclasses import dataclass, field

from sca.internal.review import DecisionType
from sca.internal.sca import Check


@dataclass
class TailoringException:
    justification: str
    exception_check: Check
    decision: DecisionType = DecisionType.EXCEPTION


@dataclass
class Tailoring:
    name: str
    id: str
    description: str
    decisions: dict[int, TailoringException] = field(default_factory=dict)
