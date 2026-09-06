'''Typed projections of Wazuh SCA policy data.'''

from dataclasses import dataclass
from typing import Any, TypeAlias

Compliance: TypeAlias = dict[str, list[str | int | float]]


@dataclass
class Check:
    compliance: list[Compliance] | None
    condition: str
    description: str | None
    id: int
    impact: str
    rationale: str | None
    references: list[str] | None
    remediation: str | None
    rules: list[str] | None
    title: str
    regex_type: str | None

    @staticmethod
    def from_dict(obj: Any) -> 'Check':
        compliance = obj.get('compliance')
        return Check(
            [dict(item) for item in compliance] if compliance else None,
            str(obj.get('condition')),
            str(obj['description']) if obj.get('description') else None,
            int(obj.get('id')),
            str(obj.get('impact')) if obj.get('impact') is not None else '',
            str(obj['rationale']) if obj.get('rationale') else None,
            list(obj['references']) if obj.get('references') else None,
            str(obj['remediation']) if obj.get('remediation') else None,
            list(obj['rules']) if obj.get('rules') else None,
            str(obj.get('title')),
            str(obj['regex_type']) if obj.get('regex_type') else None,
        )


@dataclass
class Policy:
    description: str
    file: str
    id: str
    name: str
    references: list[str] | None
    regex_type: str | None

    @staticmethod
    def from_dict(obj: Any) -> 'Policy':
        return Policy(
            str(obj.get('description')),
            str(obj.get('file')),
            str(obj.get('id')),
            str(obj.get('name')),
            list(obj['references']) if obj.get('references') else None,
            str(obj['regex_type']) if obj.get('regex_type') else None,
        )


@dataclass
class Requirements:
    condition: str
    description: str
    rules: list[str]
    title: str

    @staticmethod
    def from_dict(obj: Any) -> 'Requirements':
        return Requirements(
            str(obj.get('condition')),
            str(obj.get('description')),
            list(obj.get('rules')),
            str(obj.get('title')),
        )


@dataclass
class SCA:
    checks: list[Check]
    policy: Policy
    requirements: Requirements | None
    variables: dict | None

    @staticmethod
    def from_dict(obj: Any) -> 'SCA':
        requirements = obj.get('requirements')
        variables = obj.get('variables')
        return SCA(
            [Check.from_dict(item) for item in obj.get('checks')],
            Policy.from_dict(obj.get('policy')),
            Requirements.from_dict(requirements) if requirements is not None else None,
            dict(variables) if variables else None,
        )
