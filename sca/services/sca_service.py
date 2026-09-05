"""SCA Service - Business logic for SCA operations."""
import os
from typing import Any

from ruamel.yaml import YAML

from sca.internal.guide import Guide
from sca.internal.loosening import Tailoring, TailoringException
from sca.internal.review import DecisionType, normalize_decisions
from sca.internal.sca import SCA, Check


class SCAService:
    """Service for handling SCA file operations."""

    @staticmethod
    def validate_sca_file(filepath: str) -> tuple[bool, str | None]:
        """Validate a policy against the documented Wazuh SCA structure."""
        try:
            if not os.path.exists(filepath):
                return False, "File not found"

            yaml = YAML(typ='safe')
            with open(filepath, 'r', encoding='UTF-8') as f:
                data = yaml.load(f)

            if not isinstance(data, dict):
                return False, "Invalid YAML format: root must be a mapping"

            policy = data.get('policy')
            if not isinstance(policy, dict):
                return False, "Missing or invalid 'policy' section: expected a mapping"
            for field in ('name', 'id', 'description', 'file'):
                if field not in policy or not isinstance(policy[field], str) or not policy[field].strip():
                    return False, f"Missing required field in policy: {field}"
            if 'references' in policy:
                references = policy['references']
                if not isinstance(references, list) or not all(isinstance(v, str) for v in references):
                    return False, "Optional field 'policy.references' must be an array of strings"
            if 'regex_type' in policy and policy['regex_type'] not in {'osregex', 'pcre2'}:
                return False, "Optional field 'policy.regex_type' must be 'osregex' or 'pcre2'"

            requirements = data.get('requirements')
            if requirements is not None:
                if not isinstance(requirements, dict):
                    return False, "Optional 'requirements' section must be a mapping"
                for field in ('title', 'description', 'condition'):
                    if field not in requirements or not isinstance(requirements[field], str) or not requirements[field].strip():
                        return False, f"Missing required field in requirements: {field}"
                rules = requirements.get('rules')
                if not isinstance(rules, list) or not rules or not all(
                        isinstance(v, str) and v.strip() for v in rules):
                    return False, "requirements.rules must be a non-empty array of strings"

            checks = data.get('checks')
            if not isinstance(checks, list):
                return False, "Missing or invalid 'checks' section: expected an array"
            if not checks:
                return False, "At least one check is required"

            ids = set()
            compliance_fields = {
                'cis', 'cis_csc_v8', 'cis_csc_v7', 'nist_sp_800-53',
                'iso_27001-2013', 'cmmc_v2.0', 'pci_dss_v3.2.1',
                'pci_dss_v4.0', 'soc_2', 'mitre_techniques',
                'mitre_tactics', 'mitre_mitigations', 'hipaa'}
            for index, check in enumerate(checks):
                location = f"checks[{index}]"
                if not isinstance(check, dict):
                    return False, f"{location} must be a mapping"
                check_id = check.get('id')
                if type(check_id) is not int:
                    return False, f"{location}.id must be an integer"
                if check_id in ids:
                    return False, f"Duplicate check ID: {check_id}"
                ids.add(check_id)
                title = check.get('title')
                if not isinstance(title, str) or not title.strip():
                    return False, f"Check {check_id}: title must be a non-empty string"
                condition = check.get('condition')
                if condition not in {'all', 'any', 'none'}:
                    return False, f"Check {check_id}: condition must be 'all', 'any', or 'none'"
                rules = check.get('rules')
                if not isinstance(rules, list) or not rules or not all(
                        isinstance(v, str) and v.strip() for v in rules):
                    return False, f"Check {check_id}: rules must be a non-empty array of strings"
                for field in ('references', 'compliance'):
                    if field in check and not isinstance(check[field], list):
                        return False, f"Check {check_id}: {field} must be an array"
                for field in ('description', 'rationale', 'remediation', 'impact'):
                    if field in check and not isinstance(check[field], str):
                        return False, f"Check {check_id}: {field} must be a string"
                if 'references' in check and not all(isinstance(v, str) for v in check['references']):
                    return False, f"Check {check_id}: references entries must be strings"
                if 'regex_type' in check and check['regex_type'] not in {'osregex', 'pcre2'}:
                    return False, f"Check {check_id}: regex_type must be 'osregex' or 'pcre2'"
                for comp_index, compliance in enumerate(check.get('compliance', [])):
                    if not isinstance(compliance, dict):
                        return False, f"Check {check_id}: compliance[{comp_index}] must be a mapping"
                    for key, values in compliance.items():
                        if key not in compliance_fields:
                            return False, (f"Check {check_id}: compliance[{comp_index}].{key} "
                                           "is not supported")
                        if not isinstance(values, list) or not all(
                                isinstance(v, (str, int, float)) and not isinstance(v, bool)
                                for v in values):
                            return False, (f"Check {check_id}: compliance[{comp_index}].{key} "
                                           "must be an array of scalar identifiers")

            if 'variables' in data and not isinstance(data['variables'], dict):
                return False, "Optional field 'variables' must be a mapping"

            # Keep validation and parsing in lockstep: accepted input must load.
            SCA.from_dict(data)
            return True, None

        except Exception:
            return False, "Unable to parse the YAML file"

    @staticmethod
    def load_baseline(filepath: str) -> Guide:
        return Guide(baseline_path=filepath)

    @staticmethod
    def get_sca_summary(guide: Guide) -> dict[str, Any]:
        sca = guide.sca
        return {
            'policy_name': sca.policy.name,
            'policy_id': sca.policy.id,
            'policy_description': sca.policy.description,
            'total_checks': len(sca.checks),
            'checks': sca.checks
        }

    @staticmethod
    def get_checks(guide: Guide) -> list[dict[str, Any]]:
        sca: SCA = guide.sca
        checks = []
        for check in sca.checks:
            checks.append({
                'id': check.id,
                'title': check.title,
                'description': check.description or '',
                'rationale': check.rationale or '',
                'remediation': check.remediation or '',
                'impact': check.impact if hasattr(check, 'impact') else '',
                'condition': check.condition,
                'compliance': SCAService._serialize_compliance(check.compliance) if check.compliance else []
            })
        return checks

    @staticmethod
    def _serialize_compliance(compliance_list) -> list[dict[str, list[str]]]:
        result = []
        for comp in compliance_list:
            comp_dict = {}
            for field in ['cis', 'cis_csc_v8', 'cis_csc_v7', 'nist_sp_800_53',
                          'iso_27001_2013', 'cmmc_v2_0', 'pci_dss_v3_2_1',
                          'pci_dss_v4_0', 'soc_2', 'mitre_techniques',
                          'mitre_tactics', 'mitre_mitigations', 'hipaa']:
                value = getattr(comp, field, None)
                if value:
                    comp_dict[field] = value
            result.append(comp_dict)
        return result

    @staticmethod
    def get_check_by_id(guide: Guide, check_id: int) -> dict[str, Any] | None:
        for check in guide.sca.checks:
            if check.id == check_id:
                return {
                    'id': check.id, 'title': check.title,
                    'description': check.description or '',
                    'rationale': check.rationale or '',
                    'remediation': check.remediation or '',
                    'impact': check.impact, 'condition': check.condition,
                    'compliance': SCAService._serialize_compliance(check.compliance)
                    if check.compliance else []}
        return None

    @staticmethod
    def calculate_stats(guide: Guide, decisions: dict[str, Any]) -> dict[str, Any]:
        baseline_ids = {check['id'] for check in SCAService.get_checks(guide)}
        normalized = normalize_decisions(decisions, baseline_ids)
        accepted = sum(d.decision is DecisionType.ACCEPTED for d in normalized.values())
        exceptions = sum(d.decision is DecisionType.EXCEPTION for d in normalized.values())
        total = len(baseline_ids)
        reviewed = accepted + exceptions
        return {
            'total': total, 'unreviewed': total - reviewed,
            'accepted': accepted, 'exceptions': exceptions,
            'effective_included': total - exceptions, 'reviewed': reviewed,
            'review_completion': (reviewed / total * 100) if total else 0,
        }

    @staticmethod
    def create_tailoring(name: str, custom_id: str, description: str) -> Tailoring:
        return Tailoring(name=name, id=custom_id, description=description, decisions={})

    create_loosening = create_tailoring

    @staticmethod
    def add_exception(tailoring: Tailoring, check: Check, justification: str) -> None:
        tailoring.decisions[check.id] = TailoringException(
            justification=justification, exception_check=check)

    add_decision = add_exception

    @staticmethod
    def remove_exception(tailoring: Tailoring, check_id: int) -> None:
        if check_id in tailoring.decisions:
            del tailoring.decisions[check_id]

    remove_decision = remove_exception
