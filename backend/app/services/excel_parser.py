"""
Excel BOM Parser Service
Extracts manufacturing data from Excel BOM files
"""

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

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
            
            # Read Excel file without headers first (to detect header row)
            df_raw = pd.read_excel(file_path, engine='openpyxl', sheet_name=0, header=None)
            
            # Step 2: Auto-detect header row
            header_row = self._find_header_row(df_raw)
            logger.info(f"[BOM Parser] Detected header row: {header_row}")
            
            # Re-read with correct header
            if header_row >= 0:
                df = pd.read_excel(file_path, engine='openpyxl', sheet_name=0, header=header_row)
            else:
                df = df_raw
            
            # Log detected column names for debugging
            logger.info(f"[BOM Parser] Column headers: {list(df.columns[:10])}")
            
            # Step 2.5: Map columns by name (not position) for flexibility
            col_map = self._map_columns(df)
            logger.info(f"[BOM Parser] Column mapping: {col_map}")
            
            # Step 3: Extract job number
            job_number = self._extract_job_number(df, col_map)
            
            # Step 4-5: Extract parts with revisions
            parts = self._extract_parts(df, col_map)
            
            logger.info(f"[BOM Parser] Successfully read {file_name}: "
                       f"{len(df)} rows, {len(df.columns)} columns | "
                       f"Job: {job_number}, Parts: {len(parts)}")
            
            return {
                "file_name": file_name,
                "status": "success",
                "total_rows": len(df),
                "total_columns": len(df.columns),
                "header_row": header_row,
                "column_mapping": col_map,
                "job_number": job_number,
                "parts": parts,
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
    
    def _map_columns(self, df: pd.DataFrame) -> Dict[str, Optional[str]]:
        """
        Map expected columns by detecting their names (not positions).
        
        This handles varying Excel formats where columns may be in different orders.
        
        Args:
            df: DataFrame with column headers
            
        Returns:
            Dictionary mapping logical names to actual column names
        """
        col_map = {
            "job": None,
            "part_number": None,
            "description": None,
            "revision": None,
            "qty": None
        }
        
        # Normalize column names for matching
        columns_lower = {str(col).lower().strip(): col for col in df.columns}
        
        # Detect Job column
        for pattern in ['job', 'job #', 'job number', 'work order']:
            if pattern in columns_lower:
                col_map["job"] = columns_lower[pattern]
                break
        
        # Detect Part Number column
        # Note: "Assembly" often contains actual part numbers, check it first
        for pattern in ['assembly', 'part #', 'part number', 'part', 'item', 'item number']:
            if pattern in columns_lower:
                col_map["part_number"] = columns_lower[pattern]
                break
        
        # Detect Description column
        for pattern in ['description', 'desc', 'part description']:
            if pattern in columns_lower:
                col_map["description"] = columns_lower[pattern]
                break
        
        # Detect Revision column
        # Note: "Assy Rev" (Assembly Revision) contains revision info
        for pattern in ['assy rev', 'assembly rev', 'revision', 'rev', 'rev #']:
            if pattern in columns_lower:
                col_map["revision"] = columns_lower[pattern]
                break
        
        # Detect Quantity column
        for pattern in ['qty', 'quantity', 'qnty']:
            if pattern in columns_lower:
                col_map["qty"] = columns_lower[pattern]
                break
        
        return col_map
    
    def _extract_job_number(self, df: pd.DataFrame, col_map: Dict[str, Optional[str]]) -> Optional[str]:
        """
        Extract 5-digit job number from the Job column.
        
        Args:
            df: DataFrame with parsed data
            col_map: Column mapping from _map_columns()
            
        Returns:
            5-digit job number string, or None if not found
        """
        if not col_map["job"]:
            logger.warning("[BOM Parser] Job column not found, cannot extract job number")
            return None
        
        job_col = col_map["job"]
        
        # Search first 20 rows for 5-digit job number
        for value in df[job_col].head(20).dropna():
            # Extract digits only
            digits = re.sub(r'\D', '', str(value))
            if len(digits) == 5:
                logger.info(f"[BOM Parser] Found job number: {digits}")
                return digits
        
        logger.warning("[BOM Parser] No 5-digit job number found")
        return None
    
    def _extract_parts(self, df: pd.DataFrame, col_map: Dict[str, Optional[str]]) -> List[Dict[str, Any]]:
        """
        Extract all parts with part numbers and revisions.
        
        Uses pattern matching to identify valid part numbers:
        - 3+ letter prefix, dash, numbers/letters (e.g., PCA-1052-05, DRW-1608-03, SWC-400)
        
        Args:
            df: DataFrame with parsed data
            col_map: Column mapping from _map_columns()
            
        Returns:
            List of dicts with part_number, revision, row_number
        """
        if not col_map["part_number"]:
            logger.warning("[BOM Parser] Part Number column not found")
            return []
        
        parts = []
        part_col = col_map["part_number"]
        rev_col = col_map["revision"]
        
        # Pattern for part numbers: 3+ letters, dash, alphanumeric
        # Matches: PCA-1052-05, DRW-1608-03, SWC-400, INF-1619, etc.
        part_pattern = re.compile(r'^[A-Z]{3,}-[A-Z0-9-]+$', re.IGNORECASE)
        
        for idx, row in df.iterrows():
            part_value = str(row[part_col]).strip().upper()
            
            # Skip empty/invalid values
            if part_value in ['NAN', '', 'NONE']:
                continue
            
            # Check if matches part number pattern
            if part_pattern.match(part_value):
                part_data = {
                    "part_number": part_value,
                    "row_number": int(idx) + 1,  # 1-indexed
                    "revision": None
                }
                
                # Extract revision if column exists
                if rev_col and pd.notna(row[rev_col]):
                    revision = str(row[rev_col]).strip().upper()
                    # Normalize revision (remove "REV" prefix if present)
                    revision = re.sub(r'^REV\s*', '', revision, flags=re.IGNORECASE)
                    if revision and revision != 'NAN':
                        part_data["revision"] = revision
                
                parts.append(part_data)
        
        logger.info(f"[BOM Parser] Extracted {len(parts)} parts")
        return parts
    
    def inspect_file_structure(self, file_path: str) -> Dict[str, Any]:
        """
        DEBUG: Inspect Excel file structure to understand column layout
        """
        try:
            df_raw = pd.read_excel(file_path, engine='openpyxl', sheet_name=0, header=None, nrows=10)
            
            result = {
                "file_name": Path(file_path).name,
                "rows": []
            }
            
            for idx in range(len(df_raw)):
                row_data = df_raw.iloc[idx].tolist()
                result["rows"].append({
                    "row_index": idx,
                    "values": row_data[:10]  # First 10 columns
                })
            
            return result
        except Exception as e:
            return {"error": str(e)}
    
    def _find_header_row(self, df: pd.DataFrame) -> int:
        """
        Auto-detect which row contains column headers.
        
        Searches first 10 rows for keywords like 'Job', 'Part', 'Work Order' in Column A.
        
        Args:
            df: DataFrame read without headers (header=None)
            
        Returns:
            Row index (0-based) where headers are located, or 0 if not found
        """
        # Check first 10 rows only (headers are typically at the top)
        max_rows_to_check = min(10, len(df))
        
        # Keywords that indicate header row (Column A typically has "Job" or "Work Order")
        header_keywords = ['job', 'work order', 'part', 'item', 'qty']
        
        for idx in range(max_rows_to_check):
            # Check Column A (first column)
            cell_value = str(df.iloc[idx, 0]).lower().strip()
            # If any keyword found, this is likely the header row
            if any(keyword in cell_value for keyword in header_keywords):
                return idx
        
        # No header row detected, assume data starts at row 0
        return 0


class BOMAggregator:
    """
    Aggregates data from multiple BOM files for cross-validation.
    
    Combines job numbers, parts, and revisions from all parsed BOMs
    to provide unified access for validation checks.
    """
    
    def __init__(self):
        self.bom_data: List[Dict[str, Any]] = []
    
    def add_bom(self, parsed_bom: Dict[str, Any]) -> None:
        """
        Add a parsed BOM file to the aggregator.
        
        Args:
            parsed_bom: Result from ExcelBOMParser.parse_bom()
        """
        if parsed_bom.get("status") == "success":
            self.bom_data.append(parsed_bom)
            logger.info(f"[BOM Aggregator] Added {parsed_bom['file_name']}: "
                       f"Job {parsed_bom.get('job_number')}, "
                       f"{len(parsed_bom.get('parts', []))} parts")
    
    def get_all_jobs(self) -> List[str]:
        """
        Get all unique job numbers from all BOMs.
        
        Returns:
            List of unique 5-digit job numbers
        """
        jobs = set()
        for bom in self.bom_data:
            job = bom.get("job_number")
            if job:
                jobs.add(job)
        return sorted(list(jobs))
    
    def find_part(self, part_number: str) -> Optional[Dict[str, Any]]:
        """
        Find a part number across all BOMs.
        
        Args:
            part_number: Part number to search for (e.g., "PCA-1153-03")
            
        Returns:
            Dict with part info, revision, source file, or None if not found
        """
        part_number_normalized = part_number.strip().upper()
        
        for bom in self.bom_data:
            for part in bom.get("parts", []):
                if part["part_number"] == part_number_normalized:
                    return {
                        "part_number": part["part_number"],
                        "revision": part.get("revision"),
                        "row_number": part.get("row_number"),
                        "source_file": bom["file_name"],
                        "job_number": bom.get("job_number")
                    }
        
        return None
    
    def get_part_revisions(self, part_number: str) -> List[str]:
        """
        Get all revisions for a part number across all BOMs.
        
        Args:
            part_number: Part number to search for
            
        Returns:
            List of unique revisions (e.g., ['F', 'E'])
        """
        part_number_normalized = part_number.strip().upper()
        revisions = set()
        
        for bom in self.bom_data:
            for part in bom.get("parts", []):
                if part["part_number"] == part_number_normalized:
                    rev = part.get("revision")
                    if rev:
                        revisions.add(rev)
        
        return sorted(list(revisions))
    
    def get_all_parts(self) -> List[str]:
        """
        Get all unique part numbers from all BOMs.
        
        Returns:
            List of unique part numbers
        """
        parts = set()
        for bom in self.bom_data:
            for part in bom.get("parts", []):
                parts.add(part["part_number"])
        return sorted(list(parts))
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get summary statistics of aggregated BOM data.
        
        Returns:
            Summary with counts and lists of jobs/parts
        """
        all_jobs = self.get_all_jobs()
        all_parts = self.get_all_parts()
        
        return {
            "total_bom_files": len(self.bom_data),
            "total_jobs": len(all_jobs),
            "total_unique_parts": len(all_parts),
            "jobs": all_jobs,
            "parts": all_parts,
            "bom_files": [bom["file_name"] for bom in self.bom_data]
        }
    
    def clear(self) -> None:
        """Clear all aggregated BOM data."""
        self.bom_data.clear()


# Singleton instances
excel_parser = ExcelBOMParser()
bom_aggregator = BOMAggregator()

