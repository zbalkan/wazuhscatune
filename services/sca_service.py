"""SCA Service - Business logic for SCA operations."""
import os
from typing import Optional, Dict, Any
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap

from internal.guide import Guide
from internal.sca import SCA, Check
from internal.loosening import Loosening, Decision


class SCAService:
    """Service for handling SCA file operations."""
    
    @staticmethod
    def validate_sca_file(filepath: str) -> tuple[bool, Optional[str]]:
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
            
            yaml = YAML()
            with open(filepath, 'r', encoding='UTF-8') as f:
                data = yaml.load(f)
            
            # Check required sections
            if not isinstance(data, dict):
                return False, "Invalid YAML format: root must be a dictionary"
            
            if 'policy' not in data:
                return False, "Missing 'policy' section"
            
            policy = data['policy']
            required_policy_fields = ['name', 'id', 'description', 'file']
            for field in required_policy_fields:
                if field not in policy:
                    return False, f"Missing required field in policy: {field}"
            
            if 'checks' not in data:
                return False, "Missing 'checks' section"
            
            if not isinstance(data['checks'], list):
                return False, "'checks' must be an array"
            
            if len(data['checks']) == 0:
                return False, "At least one check is required"
            
            return True, None
            
        except Exception as e:
            return False, f"Error parsing YAML: {str(e)}"
    
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
    def get_sca_summary(guide: Guide) -> Dict[str, Any]:
        """
        Extract policy info and check statistics.
        
        Args:
            guide: Guide object
            
        Returns:
            Dictionary with policy info and statistics
        """
        sca = SCA.from_dict(guide.__sca_yml__)
        
        return {
            'policy_name': sca.policy.name,
            'policy_id': sca.policy.id,
            'policy_description': sca.policy.description,
            'total_checks': len(sca.checks),
            'checks': sca.checks
        }
    
    @staticmethod
    def get_checks(guide: Guide) -> list[Dict[str, Any]]:
        """
        Return list of all checks with serializable data.
        
        Args:
            guide: Guide object
            
        Returns:
            List of check dictionaries
        """
        sca = SCA.from_dict(guide.__sca_yml__)
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
    def _serialize_compliance(compliance_list) -> list[Dict[str, list[str]]]:
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
    def get_check_by_id(guide: Guide, check_id: int) -> Optional[Dict[str, Any]]:
        """
        Get specific check details.
        
        Args:
            guide: Guide object
            check_id: Check ID to retrieve
            
        Returns:
            Check dictionary or None if not found
        """
        checks = SCAService.get_checks(guide)
        for check in checks:
            if check['id'] == check_id:
                return check
        return None
    
    @staticmethod
    def create_loosening(name: str, custom_id: str, description: str) -> Loosening:
        """
        Create new Loosening object.
        
        Args:
            name: Custom policy name
            custom_id: Custom policy ID
            description: Custom policy description
            
        Returns:
            Loosening object
        """
        return Loosening(
            name=name,
            id=custom_id,
            description=description,
            decisions={}
        )
    
    @staticmethod
    def add_decision(loosening: Loosening, check: Check, justification: str) -> None:
        """
        Add exclusion decision to loosening.
        
        Args:
            loosening: Loosening object
            check: Check object to exclude
            justification: Justification for exclusion
        """
        decision = Decision(
            justification=justification,
            suppressed_check=check
        )
        loosening.decisions[check.id] = decision
    
    @staticmethod
    def remove_decision(loosening: Loosening, check_id: int) -> None:
        """
        Remove exclusion decision from loosening.
        
        Args:
            loosening: Loosening object
            check_id: Check ID to remove
        """
        if check_id in loosening.decisions:
            del loosening.decisions[check_id]
