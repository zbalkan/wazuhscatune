"""SCA validation and review helpers."""
import os
from typing import Any

from ruamel.yaml import YAML

from sca.internal.guide import Guide
from sca.internal.loosening import Tailoring, TailoringException
from sca.internal.review import DecisionType, normalize_decisions
from sca.internal.sca import Check, SCA


def validate_sca_file(filepath: str) -> tuple[bool, str | None]:
    try:
        if not os.path.exists(filepath):
            return False, "File not found"

        yaml = YAML(typ='safe')
        with open(filepath, 'r', encoding='UTF-8') as stream:
            data = yaml.load(stream)

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
            if not isinstance(references, list) or not all(isinstance(value, str) for value in references):
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
                    isinstance(value, str) and value.strip() for value in rules):
                return False, "requirements.rules must be a non-empty array of strings"

        checks = data.get('checks')
        if not isinstance(checks, list):
            return False, "Missing or invalid 'checks' section: expected an array"
        if not checks:
            return False, "At least one check is required"

        ids = set()
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
            if check.get('condition') not in {'all', 'any', 'none'}:
                return False, f"Check {check_id}: condition must be 'all', 'any', or 'none'"

            rules = check.get('rules')
            if not isinstance(rules, list) or not rules or not all(
                    isinstance(value, str) and value.strip() for value in rules):
                return False, f"Check {check_id}: rules must be a non-empty array of strings"

            for field in ('references', 'compliance'):
                if field in check and not isinstance(check[field], list):
                    return False, f"Check {check_id}: {field} must be an array"
            for field in ('description', 'rationale', 'remediation', 'impact'):
                if field in check and not isinstance(check[field], str):
                    return False, f"Check {check_id}: {field} must be a string"
            if 'references' in check and not all(isinstance(value, str) for value in check['references']):
                return False, f"Check {check_id}: references entries must be strings"
            if 'regex_type' in check and check['regex_type'] not in {'osregex', 'pcre2'}:
                return False, f"Check {check_id}: regex_type must be 'osregex' or 'pcre2'"

            for comp_index, compliance in enumerate(check.get('compliance', [])):
                if not isinstance(compliance, dict):
                    return False, f"Check {check_id}: compliance[{comp_index}] must be a mapping"
                for key, values in compliance.items():
                    if not isinstance(key, str) or not key.strip():
                        return False, f"Check {check_id}: compliance framework names must be non-empty strings"
                    if not isinstance(values, list) or not all(
                            isinstance(value, (str, int, float)) and not isinstance(value, bool)
                            for value in values):
                        return False, (f"Check {check_id}: compliance[{comp_index}].{key} "
                                       "must be an array of scalar identifiers")

        if 'variables' in data and not isinstance(data['variables'], dict):
            return False, "Optional field 'variables' must be a mapping"

        SCA.from_dict(data)
        return True, None
    except Exception:
        return False, "Unable to parse the YAML file"


def get_checks(guide: Guide) -> list[dict[str, Any]]:
    return [
        {
            'id': check.id,
            'title': check.title,
            'description': check.description or '',
            'rationale': check.rationale or '',
            'remediation': check.remediation or '',
            'impact': check.impact,
            'condition': check.condition,
            'compliance': [dict(item) for item in check.compliance] if check.compliance else [],
        }
        for check in guide.sca.checks
    ]


def calculate_stats(guide: Guide, decisions: dict[str, Any]) -> dict[str, Any]:
    baseline_ids = {check.id for check in guide.sca.checks}
    normalized = normalize_decisions(decisions, baseline_ids)
    accepted = sum(value.decision is DecisionType.ACCEPTED for value in normalized.values())
    exceptions = sum(value.decision is DecisionType.EXCEPTION for value in normalized.values())
    total = len(baseline_ids)
    reviewed = accepted + exceptions
    return {
        'total': total,
        'unreviewed': total - reviewed,
        'accepted': accepted,
        'exceptions': exceptions,
        'effective_included': total - exceptions,
        'reviewed': reviewed,
        'review_completion': (reviewed / total * 100) if total else 0,
    }


def create_tailoring(name: str, custom_id: str, description: str) -> Tailoring:
    return Tailoring(name=name, id=custom_id, description=description, decisions={})


def add_exception(tailoring: Tailoring, check: Check, justification: str) -> None:
    tailoring.decisions[check.id] = TailoringException(
        justification=justification,
        exception_check=check,
    )
