"""Export Service - File generation logic."""
import logging
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
    """Service for handling file export operations."""

    @staticmethod
    def generate_files(guide: Guide, tailoring: Tailoring,
                       base_filename: str, export_root: str | None = None) -> tuple[str, str, str, str]:
        """
        Create a tailored SCA policy and exception records.

        Args:
            guide: Guide object with baseline data
            tailoring: Tailoring object with exceptions
            base_filename: Base name for output files

        Returns:
            Paths to the policy, YAML record, Markdown record, and temporary directory.
        """
        # Create temporary directory for generated files
        if not re.fullmatch(r'[a-z0-9][a-z0-9_]*', base_filename):
            raise ValueError("Invalid export filename")
        root: Path = Path(export_root or tempfile.gettempdir()).resolve()
        root.mkdir(parents=True, exist_ok=True)
        temp_dir = str(root / str(uuid.uuid4()))
        os.mkdir(temp_dir)

        # Generate file paths
        custom_sca_path: str = os.path.join(temp_dir, f"{base_filename}.yml")
        exceptions_yml_path: str = os.path.join(temp_dir, f"{base_filename}_exceptions.yml")
        exceptions_md_path: str = os.path.join(temp_dir, f"{base_filename}_exceptions.md")

        try:
            guide.import_tailoring(tailoring)
            guide.export_custom(custom_path=custom_sca_path)
            exceptions_yml_path, exceptions_md_path = guide.export_exceptions(
                yml_path=exceptions_yml_path, md_path=exceptions_md_path)
        except Exception:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise

        return custom_sca_path, exceptions_yml_path, exceptions_md_path, temp_dir

    @staticmethod
    def create_zip_archive(files: list[str], archive_name: str,
                           export_root: str | None = None) -> str:
        """
        Bundle files into ZIP archive.

        Args:
            files: List of file paths to include
            archive_name: Name for the ZIP file

        Returns:
            Path to created ZIP file
        """
        if Path(archive_name).name != archive_name or not archive_name.endswith('.zip'):
            raise ValueError("Invalid archive filename")
        root: Path = Path(export_root or tempfile.gettempdir()).resolve()
        root.mkdir(parents=True, exist_ok=True)
        temp_dir = str(root / str(uuid.uuid4()))
        os.mkdir(temp_dir)
        zip_path: str = os.path.join(temp_dir, archive_name)

        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in files:
                    if not os.path.isfile(file_path):
                        raise FileNotFoundError(f"Promised export artifact is missing: {file_path}")
                    zipf.write(file_path, os.path.basename(file_path))
        except Exception:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise

        return zip_path

    @staticmethod
    def cleanup_temp_files(*paths: str) -> None:
        """
        Remove temporary files and directories.

        Args:
            *paths: Variable number of file/directory paths to remove
        """
        for path in paths:
            try:
                if os.path.isfile(path):
                    os.remove(path)
                elif os.path.isdir(path):
                    shutil.rmtree(path)
            except Exception:
                logging.getLogger(__name__).warning(
                    "Unable to clean up export path %s", path, exc_info=True)
