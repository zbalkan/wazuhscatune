from dataclasses import dataclass

from sca.internal.sca import Check


@dataclass
class TailoringException:
    justification: str
    exception_check: Check

    @property
    def suppressed_check(self) -> Check:
        """Compatibility accessor for the pre-0.2 field name."""
        return self.exception_check


@dataclass
class Tailoring:
    name: str
    id: str
    description: str
    decisions: dict[int, TailoringException]

    def get_ids(self) -> list[int]:
        if self.decisions:
            return [k for k, _ in self.decisions.items()]
        else:
            return []


# Compatibility aliases for callers of the pre-0.2 internal API.
Decision = TailoringException
Loosening = Tailoring
