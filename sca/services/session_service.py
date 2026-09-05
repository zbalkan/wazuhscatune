"""Contained draft persistence and lifecycle cleanup."""
import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Any

logger: logging.Logger = logging.getLogger(__name__)
SESSION_ID: re.Pattern[str] = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$", re.I)


def contained_path(root: str, name: str) -> Path:
    """Return a path below root or reject traversal and absolute paths."""
    base: Path = Path(root).resolve()
    candidate: Path = (base / name).resolve()
    if candidate == base or base not in candidate.parents:
        raise ValueError("Path is outside the configured application directory")
    return candidate


def validate_contained(root: str, path: str) -> Path:
    """Validate an existing absolute or relative path is beneath root."""
    base: Path = Path(root).resolve()
    candidate: Path = Path(path).resolve()
    if base not in candidate.parents:
        raise ValueError("Path is outside the configured application directory")
    return candidate


class SessionService:
    def __init__(self, draft_folder: str) -> None:
        self.draft_folder = str(Path(draft_folder).resolve())
        os.makedirs(self.draft_folder, exist_ok=True)

    @staticmethod
    def validate_session_id(session_id: object) -> str:
        if not isinstance(session_id, str) or not SESSION_ID.fullmatch(session_id):
            raise ValueError("Invalid session identifier")
        return session_id

    def _get_draft_path(self, session_id: str) -> Path:
        return contained_path(self.draft_folder,
                              f"{self.validate_session_id(session_id)}.json")

    def save_draft(self, session_id: str, data: dict[str, Any]) -> bool:
        try:
            payload: dict[str, Any] = dict(data)
            payload['last_saved'] = time.time()
            with self._get_draft_path(session_id).open('w', encoding='utf-8') as stream:
                json.dump(payload, stream, indent=2, ensure_ascii=False)
            return True
        except Exception:
            logger.exception("Unable to save draft %s", session_id)
            return False

    def load_draft(self, session_id: str) -> dict[str, Any] | None:
        try:
            path: Path = self._get_draft_path(session_id)
            if not path.is_file():
                return None
            with path.open(encoding='utf-8') as stream:
                data = json.load(stream)
            return data if isinstance(data, dict) else None
        except Exception:
            logger.exception("Unable to load draft %s", session_id)
            return None

    def delete_draft(self, session_id: str) -> bool:
        try:
            self._get_draft_path(session_id).unlink(missing_ok=True)
            return True
        except Exception:
            logger.exception("Unable to delete draft %s", session_id)
            return False

    def list_drafts(self) -> list[dict[str, Any]]:
        """Return safe metadata for recoverable drafts, newest first."""
        drafts: list[dict[str, Any]] = []
        for path in Path(self.draft_folder).glob('*.json'):
            session_id = path.stem
            if not SESSION_ID.fullmatch(session_id):
                continue
            data: dict[str, Any] | None = self.load_draft(session_id)
            if data and isinstance(data.get('custom_name'), str):
                saved = data.get('last_saved', 0)
                if not isinstance(saved, (int, float)):
                    saved = 0
                drafts.append({'session_id': session_id,
                               'custom_name': data['custom_name'],
                               'last_saved': saved})
        return sorted(drafts, key=lambda item: item['last_saved'], reverse=True)

    @staticmethod
    def serialize_session_data(baseline_filename: str, custom_name: str,
                               sanitized_name: str, custom_description: str,
                               decisions: dict[str, Any]) -> dict[str, Any]:
        return {'baseline_filename': baseline_filename, 'custom_name': custom_name,
                'sanitized_name': sanitized_name,
                'custom_description': custom_description, 'decisions': decisions}

    @staticmethod
    def cleanup_expired(roots: list[str], ttl_hours: int) -> None:
        cutoff: float = time.time() - max(ttl_hours, 1) * 3600
        for root_name in roots:
            root: Path = Path(root_name).resolve()
            if not root.is_dir():
                continue
            for path in root.iterdir():
                try:
                    if path.is_symlink() or path.stat().st_mtime >= cutoff:
                        continue
                    if path.is_file():
                        path.unlink()
                    elif path.is_dir():
                        import shutil
                        shutil.rmtree(path)
                except Exception:
                    logger.warning("Unable to remove expired path %s", path,
                                   exc_info=True)
