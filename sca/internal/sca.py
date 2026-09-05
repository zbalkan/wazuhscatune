'''
Reference:
https://documentation.wazuh.com/current/user-manual/capabilities/sec-config-assessment/creating-custom-policies.html
'''

from dataclasses import dataclass
from typing import Any


@dataclass
class Compliance:
    cis: list[str] | None
    cis_csc_v8: list[str] | None
    cis_csc_v7: list[str] | None
    nist_sp_800_53: list[str] | None
    iso_27001_2013: list[str] | None
    cmmc_v2_0: list[str] | None
    pci_dss_v3_2_1: list[str] | None
    pci_dss_v4_0: list[str] | None
    soc_2: list[str] | None
    mitre_techniques: list[str] | None
    mitre_tactics: list[str] | None
    mitre_mitigations: list[str] | None
    hipaa: list[str] | None

    @staticmethod
    def from_dict(obj: Any) -> 'Compliance':
        values = {
            'cis': obj.get('cis'), 'cis_csc_v8': obj.get('cis_csc_v8'),
            'cis_csc_v7': obj.get('cis_csc_v7'), 'nist_sp_800_53': obj.get('nist_sp_800-53'),
            'iso_27001_2013': obj.get('iso_27001-2013'), 'cmmc_v2_0': obj.get('cmmc_v2.0'),
            'pci_dss_v3_2_1': obj.get('pci_dss_v3.2.1'), 'pci_dss_v4_0': obj.get('pci_dss_v4.0'),
            'soc_2': obj.get('soc_2'), 'mitre_techniques': obj.get('mitre_techniques'),
            'mitre_tactics': obj.get('mitre_tactics'), 'mitre_mitigations': obj.get('mitre_mitigations'),
            'hipaa': obj.get('hipaa')}
        return Compliance(**{key: list(value) if value else None for key, value in values.items()})


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
            [Compliance.from_dict(y) for y in compliance] if compliance else None,
            str(obj.get('condition')),
            str(obj['description']) if obj.get('description') else None,
            int(obj.get('id')),
            str(obj.get('impact')) if obj.get('impact') is not None else '',
            str(obj['rationale']) if obj.get('rationale') else None,
            list(obj['references']) if obj.get('references') else None,
            str(obj['remediation']) if obj.get('remediation') else None,
            list(obj['rules']) if obj.get('rules') else None,
            str(obj.get('title')),
            str(obj['regex_type']) if obj.get('regex_type') else None)


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
            str(obj.get('description')), str(obj.get('file')), str(obj.get('id')),
            str(obj.get('name')), list(obj['references']) if obj.get('references') else None,
            str(obj['regex_type']) if obj.get('regex_type') else None)


@dataclass
class Requirements:
    condition: str
    description: str
    rules: list[str]
    title: str

    @staticmethod
    def from_dict(obj: Any) -> 'Requirements':
        return Requirements(
            str(obj.get('condition')), str(obj.get('description')),
            list(obj.get('rules')), str(obj.get('title')))


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
            [Check.from_dict(y) for y in obj.get('checks')],
            Policy.from_dict(obj.get('policy')),
            Requirements.from_dict(requirements) if requirements is not None else None,
            dict(variables) if variables else None)
