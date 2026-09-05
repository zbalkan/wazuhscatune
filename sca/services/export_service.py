"""File generation helpers."""
import os
import re
import shutil
import tempfile
import uuid
import zipfile
from pathlib import Path

from sca.internal.guide import Guide
from sca.internal.loosening import Tailoring


class ExportService:
    @staticmethod
    def generate_files(guide: Guide, tailoring: Tailoring,
                       base_filename: str, export_root: str | None = None) -> tuple[str, str, str, str]:
        if not re.fullmatch(r'[a-z0-9][a-z0-9_]*', base_filename):
            raise ValueError("Invalid export filename")
        root = Path(export_root or tempfile.gettempdir()).resolve()
        root.mkdir(parents=True, exist_ok=True)
        temp_dir = str(root / str(uuid.uuid4()))
        os.mkdir(temp_dir)

        custom_path = os.path.join(temp_dir, f"{base_filename}.yml")
        exceptions_yml = os.path.join(temp_dir, f"{base_filename}_exceptions.yml")
        exceptions_md = os.path.join(temp_dir, f"{base_filename}_exceptions.md")
        try:
            guide.export_custom(tailoring, custom_path)
            guide.export_exceptions(tailoring, exceptions_yml, exceptions_md)
        except Exception:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise
        return custom_path, exceptions_yml, exceptions_md, temp_dir

    @staticmethod
    def create_zip_archive(files: list[str], archive_name: str,
                           export_root: str | None = None) -> str:
        if Path(archive_name).name != archive_name or not archive_name.endswith('.zip'):
            raise ValueError("Invalid archive filename")
        root = Path(export_root or tempfile.gettempdir()).resolve()
        root.mkdir(parents=True, exist_ok=True)
        temp_dir = str(root / str(uuid.uuid4()))
        os.mkdir(temp_dir)
        zip_path = os.path.join(temp_dir, archive_name)
        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as archive:
                for file_path in files:
                    if not os.path.isfile(file_path):
                        raise FileNotFoundError(f"Promised export artifact is missing: {file_path}")
                    archive.write(file_path, os.path.basename(file_path))
        except Exception:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise
        return zip_path

    @staticmethod
    def cleanup_temp_files(*paths: str) -> None:
        for path in paths:
            if os.path.isfile(path):
                os.remove(path)
            elif os.path.isdir(path):
                shutil.rmtree(path)
