from dataclasses import dataclass

from sca.internal.sca import Check


@dataclass
class TailoringException:
    justification: str
    exception_check: Check


@dataclass
class Tailoring:
    name: str
    id: str
    description: str
    decisions: dict[int, TailoringException]
