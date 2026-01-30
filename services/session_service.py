"""Session Service - Session and draft management."""
import os
import json
from typing import Optional, Dict, Any
from datetime import datetime


class SessionService:
    """Service for handling session and draft operations."""
    
    def __init__(self, draft_folder: str):
        """
        Initialize SessionService.
        
        Args:
            draft_folder: Path to draft storage folder
        """
        self.draft_folder = draft_folder
        os.makedirs(draft_folder, exist_ok=True)
    
    def save_draft(self, session_id: str, data: Dict[str, Any]) -> bool:
        """
        Save session to JSON file.
        
        Args:
            session_id: Unique session identifier
            data: Session data to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            filepath = self._get_draft_path(session_id)
            data['last_saved'] = datetime.now().isoformat()
            
            with open(filepath, 'w', encoding='UTF-8') as f:
                json.dump(data, f, indent=2)
            
            return True
        except Exception as e:
            print(f"Error saving draft: {e}")
            return False
    
    def load_draft(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Load session from JSON file.
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            Session data or None if not found
        """
        try:
            filepath = self._get_draft_path(session_id)
            if not os.path.exists(filepath):
                return None
            
            with open(filepath, 'r', encoding='UTF-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading draft: {e}")
            return None
    
    def delete_draft(self, session_id: str) -> bool:
        """
        Remove draft file.
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            True if successful, False otherwise
        """
        try:
            filepath = self._get_draft_path(session_id)
            if os.path.exists(filepath):
                os.remove(filepath)
            return True
        except Exception as e:
            print(f"Error deleting draft: {e}")
            return False
    
    def _get_draft_path(self, session_id: str) -> str:
        """Get the file path for a draft."""
        return os.path.join(self.draft_folder, f"{session_id}.json")
    
    @staticmethod
    def serialize_session_data(baseline_path: str, custom_name: str, 
                              custom_description: str, decisions: Dict[int, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Prepare data for storage.
        
        Args:
            baseline_path: Path to baseline SCA file
            custom_name: Custom policy name
            custom_description: Custom policy description
            decisions: Dictionary of check decisions
            
        Returns:
            Serialized session data
        """
        return {
            'baseline_path': baseline_path,
            'custom_name': custom_name,
            'custom_description': custom_description,
            'decisions': decisions
        }
    
    @staticmethod
    def deserialize_session_data(data: Dict[str, Any]) -> tuple:
        """
        Restore data from storage.
        
        Args:
            data: Serialized session data
            
        Returns:
            Tuple of (baseline_path, custom_name, custom_description, decisions)
        """
        return (
            data.get('baseline_path', ''),
            data.get('custom_name', ''),
            data.get('custom_description', ''),
            data.get('decisions', {})
        )
