"""
Excel BOM Parser Service
Extracts manufacturing data from Excel BOM files
"""

import logging
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd

logger = logging.getLogger(__name__)


class ExcelBOMParser:
    """Parse Excel BOM files to extract job numbers, parts, and revisions"""
    
    def parse_bom(self, file_path: str) -> Dict[str, Any]:
        """
        Parse single Excel BOM file.
        
        Args:
            file_path: Path to Excel file (.xlsx or .xlsm)
            
        Returns:
            Dictionary with file info and extracted data
        """
        file_name = Path(file_path).name
        
        try:
            logger.info(f"[BOM Parser] Reading file: {file_name}")
            
            # Read Excel file (supports .xlsx and .xlsm)
            df = pd.read_excel(file_path, engine='openpyxl', sheet_name=0)
            
            logger.info(f"[BOM Parser] Successfully read {file_name}: "
                       f"{len(df)} rows, {len(df.columns)} columns")
            
            return {
                "file_name": file_name,
                "status": "success",
                "total_rows": len(df),
                "total_columns": len(df.columns),
                "job_number": None,  # Step 3
                "parts": [],  # Step 4-5
                "error": None
            }
            
        except FileNotFoundError:
            logger.error(f"[BOM Parser] File not found: {file_path}")
            return {
                "file_name": file_name,
                "status": "error",
                "error": "File not found",
                "parts": []
            }
            
        except Exception as e:
            logger.error(f"[BOM Parser] Failed to parse {file_name}: {e}")
            return {
                "file_name": file_name,
                "status": "error",
                "error": str(e),
                "parts": []
            }


# Singleton instance
excel_parser = ExcelBOMParser()

