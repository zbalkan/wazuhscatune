"""Export Service - File generation logic."""
import os
import zipfile
import tempfile
import logging
from typing import List, Tuple

from internal.guide import Guide
from internal.loosening import Loosening


class ExportService:
    """Service for handling file export operations."""
    
    @staticmethod
    def generate_files(guide: Guide, loosening: Loosening, 
                      base_filename: str) -> Tuple[str, str, str, str]:
        """
        Create custom SCA and loosening files.
        
        Args:
            guide: Guide object with baseline data
            loosening: Loosening object with decisions
            base_filename: Base name for output files
            
        Returns:
            Tuple of (custom_sca_path, loosening_yml_path, loosening_md_path, temp_dir)
        """
        # Create temporary directory for generated files
        temp_dir = tempfile.mkdtemp()
        
        # Generate file paths
        custom_sca_path = os.path.join(temp_dir, f"{base_filename}.yml")
        loosening_yml_path = os.path.join(temp_dir, f"{base_filename}_exceptions.yml")
        loosening_md_path = os.path.join(temp_dir, f"{base_filename}_exceptions.md")
        
        # Import loosening into guide
        guide.import_loosening(loosening=loosening)
        
        # Export custom SCA file
        guide.export_custom(custom_path=custom_sca_path)
        
        # Export loosening files (both YAML and Markdown)
        loosening_yml_path, loosening_md_path = guide.export_exceptions(
            yml_path=loosening_yml_path, md_path=loosening_md_path)
        
        return custom_sca_path, loosening_yml_path, loosening_md_path, temp_dir
    
    @staticmethod
    def create_zip_archive(files: List[str], archive_name: str) -> str:
        """
        Bundle files into ZIP archive.
        
        Args:
            files: List of file paths to include
            archive_name: Name for the ZIP file
            
        Returns:
            Path to created ZIP file
        """
        temp_dir = tempfile.mkdtemp()
        zip_path = os.path.join(temp_dir, archive_name)
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in files:
                if not os.path.isfile(file_path):
                    raise FileNotFoundError(f"Promised export artifact is missing: {file_path}")
                zipf.write(file_path, os.path.basename(file_path))
        
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
                    import shutil
                    shutil.rmtree(path)
            except Exception as e:
                logging.getLogger(__name__).warning(
                    "Unable to clean up export path %s", path, exc_info=True)
