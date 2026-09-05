"""SCA Service - Business logic for SCA operations."""
import os
import re
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
        """
        Validate SCA YAML file structure.

        Args:
            filepath: Path to the SCA YAML file

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            if not os.path.exists(filepath):
                return False, "File not found"

            yaml = YAML(typ='safe')
            with open(filepath, 'r', encoding='UTF-8') as f:
                data = yaml.load(f)

            if not isinstance(data, dict):
                return False, "Invalid YAML format: root must be a mapping"

            if 'policy' not in data:
                return False, "Missing 'policy' section"

            policy = data['policy']
            if not isinstance(policy, dict):
                return False, "'policy' must be a mapping"
            required_policy_fields = ['name', 'id', 'description', 'file']
            for field in required_policy_fields:
                if field not in policy or not isinstance(policy[field], str) or not policy[field].strip():
                    return False, f"Missing required field in policy: {field}"
            if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', policy['id']):
                return False, "policy.id contains unsupported characters"

            if 'references' in policy and not isinstance(policy['references'], list):
                return False, "Optional field 'policy.references' must be an array"
            if 'regex_type' in policy and not isinstance(policy['regex_type'], str):
                return False, "Optional field 'policy.regex_type' must be a string"

            requirements = data.get('requirements')
            if not isinstance(requirements, dict):
                return False, "Missing or invalid 'requirements' section: expected a mapping"
            for field in ('title', 'description', 'condition'):
                if field not in requirements or not isinstance(requirements[field], str) or not requirements[field].strip():
                    return False, f"Missing required field in requirements: {field}"
            if 'rules' in requirements and not isinstance(requirements['rules'], list):
                return False, "Optional field 'requirements.rules' must be an array"
            if 'rules' in requirements and not all(isinstance(v, str) and v.strip()
                                                   for v in requirements['rules']):
                return False, "requirements.rules entries must be non-empty strings"

            if 'checks' not in data:
                return False, "Missing 'checks' section"

            if not isinstance(data['checks'], list):
                return False, "'checks' must be an array"

            if len(data['checks']) == 0:
                return False, "At least one check is required"

            ids = set()
            compliance_fields = {
                'cis', 'cis_csc_v8', 'cis_csc_v7', 'nist_sp_800-53',
                'iso_27001-2013', 'cmmc_v2.0', 'pci_dss_v3.2.1',
                'pci_dss_v4.0', 'soc_2', 'mitre_techniques',
                'mitre_tactics', 'mitre_mitigations', 'hipaa'}
            for index, check in enumerate(data['checks']):
                location = f"checks[{index}]"
                if not isinstance(check, dict):
                    return False, f"{location} must be a mapping"
                check_id = check.get('id')
                # bool is an int subclass, but is never a valid check identifier.
                if type(check_id) is not int:
                    return False, f"{location}.id must be an integer"
                if check_id in ids:
                    return False, f"Duplicate check ID: {check_id}"
                ids.add(check_id)
                title = check.get('title')
                if not isinstance(title, str) or not title.strip():
                    return False, f"Check {check_id}: title must be a non-empty string"
                condition = check.get('condition')
                if not isinstance(condition, (str, int, float, bool)):
                    return False, f"Check {check_id}: condition must be a scalar value"
                for field in ('rules', 'references', 'compliance'):
                    if field in check and not isinstance(check[field], list):
                        return False, f"Check {check_id}: {field} must be an array"
                for field in ('description', 'rationale', 'remediation', 'impact', 'regex_type'):
                    if field in check and not isinstance(check[field], str):
                        return False, f"Check {check_id}: {field} must be a string"
                for field in ('rules', 'references'):
                    if field in check and not all(isinstance(v, str) and v.strip()
                                                  for v in check[field]):
                        return False, f"Check {check_id}: {field} entries must be non-empty strings"
                if 'rules' in check and not check['rules']:
                    return False, f"Check {check_id}: rules must not be empty"
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
        """
        Load SCA file into Guide object.

        Args:
            filepath: Path to the baseline SCA file

        Returns:
            Guide object
        """
        return Guide(baseline_path=filepath)

    @staticmethod
    def get_sca_summary(guide: Guide) -> dict[str, Any]:
        """
        Extract policy info and check statistics.

        Args:
            guide: Guide object

        Returns:
            Dictionary with policy info and statistics
        """
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
        """
        Return list of all checks with serializable data.

        Args:
            guide: Guide object

        Returns:
            List of check dictionaries
        """
        sca: SCA = guide.sca
        checks = []

        for check in sca.checks:
            check_data = {
                'id': check.id,
                'title': check.title,
                'description': check.description or '',
                'rationale': check.rationale or '',
                'remediation': check.remediation or '',
                'impact': check.impact if hasattr(check, 'impact') else '',
                'condition': check.condition,
                'compliance': SCAService._serialize_compliance(check.compliance) if check.compliance else []
            }
            checks.append(check_data)

        return checks

    @staticmethod
    def _serialize_compliance(compliance_list) -> list[dict[str, list[str]]]:
        """Serialize compliance data for JSON."""
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
        """
        Get specific check details.

        Args:
            guide: Guide object
            check_id: Check ID to retrieve

        Returns:
            Check dictionary or None if not found
        """
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
        """Calculate review statistics using only checks in the active baseline."""
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
        """Create a new tailoring record.

        Args:
            name: Custom policy name
            custom_id: Custom policy ID
            description: Custom policy description

        Returns:
            Tailoring object
        """
        return Tailoring(
            name=name,
            id=custom_id,
            description=description,
            decisions={}
        )

    create_loosening = create_tailoring

    @staticmethod
    def add_exception(tailoring: Tailoring, check: Check, justification: str) -> None:
        """Add a documented exception to a tailoring record.

        Args:
            tailoring: Tailoring object
            check: Check object to exclude
            justification: Justification for exclusion
        """
        decision = TailoringException(
            justification=justification,
            exception_check=check
        )
        tailoring.decisions[check.id] = decision

    add_decision = add_exception

    @staticmethod
    def remove_exception(tailoring: Tailoring, check_id: int) -> None:
        """Remove an exception from a tailoring record.

        Args:
            tailoring: Tailoring object
            check_id: Check ID to remove
        """
        if check_id in tailoring.decisions:
            del tailoring.decisions[check_id]

    remove_decision = remove_exception
