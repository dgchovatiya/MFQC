"""
Data Normalization Service

Normalizes extracted data from PDF, Image, and Excel sources for consistent
validation. Handles prefixes (VGN-, INF-), formatting, and case standardization.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class DataNormalizer:
    """
    Normalizes manufacturing data for cross-validation.
    
    Handles:
    - Board serial normalization (VGN- prefix)
    - Unit serial normalization (INF- prefix)
    - Part number standardization
    - Revision normalization
    """
    
    @staticmethod
    def normalize_board_serial(serial: str) -> Optional[str]:
        """
        Normalize board serial to VGN-#####-#### format.
        
        Args:
            serial: Raw board serial (e.g., "80751-0053", "VGN-80751-0053")
            
        Returns:
            Normalized serial with VGN- prefix, or None if invalid
        """
        if not serial:
            return None
        
        serial = serial.strip().upper()
        
        # Already has VGN- prefix
        if serial.startswith('VGN-'):
            # Validate format: VGN-#####-####
            if re.match(r'^VGN-\d{5}-\d{4}$', serial):
                return serial
            # Handle missing dash: VGN80751-0053 or VGN-807510053
            match = re.match(r'^VGN-?(\d{5})-?(\d{4})$', serial)
            if match:
                return f"VGN-{match.group(1)}-{match.group(2)}"
        
        # Missing VGN- prefix: 80751-0053
        match = re.match(r'^(\d{5})-?(\d{4})$', serial)
        if match:
            normalized = f"VGN-{match.group(1)}-{match.group(2)}"
            logger.info(f"[Normalizer] Board serial normalized: '{serial}' → '{normalized}'")
            return normalized
        
        logger.warning(f"[Normalizer] Invalid board serial format: '{serial}'")
        return None
    
    @staticmethod
    def normalize_unit_serial(serial: str) -> Optional[str]:
        """
        Normalize unit serial to INF-#### format.
        
        Args:
            serial: Raw unit serial (e.g., "1619", "INF-1619", "INF1619")
            
        Returns:
            Normalized serial with INF- prefix, or None if invalid
        """
        if not serial:
            return None
        
        serial = serial.strip().upper()
        
        # Already has INF- prefix
        if serial.startswith('INF'):
            # Validate format: INF-####
            if re.match(r'^INF-\d{4}$', serial):
                return serial
            # Handle missing dash: INF1619
            match = re.match(r'^INF-?(\d{4})$', serial)
            if match:
                return f"INF-{match.group(1)}"
        
        # Missing INF- prefix: 1619
        match = re.match(r'^(\d{4})$', serial)
        if match:
            normalized = f"INF-{match.group(1)}"
            logger.info(f"[Normalizer] Unit serial normalized: '{serial}' → '{normalized}'")
            return normalized
        
        logger.warning(f"[Normalizer] Invalid unit serial format: '{serial}'")
        return None
    
    @staticmethod
    def normalize_part_number(part: str) -> Optional[str]:
        """
        Normalize part number to standard format.
        
        Args:
            part: Raw part number (e.g., "pca-1052-05", "PCA-1052-05")
            
        Returns:
            Normalized part number (uppercase), or None if invalid
        """
        if not part:
            return None
        
        part = part.strip().upper()
        
        # Validate format: 3+ letters, dash, alphanumeric
        if re.match(r'^[A-Z]{3,}-[A-Z0-9-]+$', part):
            return part
        
        logger.warning(f"[Normalizer] Invalid part number format: '{part}'")
        return None
    
    @staticmethod
    def normalize_revision(revision: str) -> Optional[str]:
        """
        Normalize revision to standard format.
        
        Args:
            revision: Raw revision (e.g., "Rev F2", "f2", "REV F")
            
        Returns:
            Normalized revision (uppercase, no "REV" prefix), or None if invalid
        """
        if not revision:
            return None
        
        revision = revision.strip().upper()
        
        # Remove "REV" prefix
        revision = re.sub(r'^REV\s*', '', revision)
        
        # Strip extra spaces and punctuation
        revision = revision.strip('. -_')
        
        if revision:
            return revision
        
        return None
    
    @staticmethod
    def normalize_job_number(job: str) -> Optional[str]:
        """
        Normalize job number to 5-digit format.
        
        Args:
            job: Raw job number (e.g., "82334", "Job: 82334")
            
        Returns:
            Normalized 5-digit job number, or None if invalid
        """
        if not job:
            return None
        
        # Extract digits only
        digits = re.sub(r'\D', '', str(job))
        
        # Validate 5 digits
        if len(digits) == 5:
            return digits
        
        logger.warning(f"[Normalizer] Invalid job number format: '{job}'")
        return None
    
    def normalize_extracted_data(self, data: Dict[str, Any], source: str) -> Dict[str, Any]:
        """
        Normalize all extracted data from a source (PDF, Image, Excel).
        
        Args:
            data: Raw extracted data
            source: Source type ("traveler", "image", "bom")
            
        Returns:
            Normalized data dictionary with normalization_applied flag
        """
        logger.info(f"[Normalizer] Normalizing data from {source}")
        
        normalized = {
            "source": source,
            "job_numbers": set(),
            "board_serials": set(),
            "part_numbers": set(),
            "unit_serials": set(),
            "parts_with_revisions": [],  # [{part_number, revision}]
            "normalization_applied": []  # Track what was normalized
        }
        
        # Normalize job number(s)
        if "job_number" in data and data["job_number"]:
            job = self.normalize_job_number(data["job_number"])
            if job:
                normalized["job_numbers"].add(job)
        
        # Normalize job numbers list (for BOM aggregator)
        if "job_numbers" in data:
            if isinstance(data["job_numbers"], list):
                for job_num in data["job_numbers"]:
                    job = self.normalize_job_number(job_num)
                    if job:
                        normalized["job_numbers"].add(job)
        
        # Normalize board serials
        if "board_serials" in data:
            for serial in data["board_serials"]:
                norm_serial = self.normalize_board_serial(serial)
                if norm_serial:
                    normalized["board_serials"].add(norm_serial)
                    if norm_serial != serial.strip().upper():
                        normalized["normalization_applied"].append(
                            f"Board serial: '{serial}' → '{norm_serial}'"
                        )
        
        # Normalize unit serial
        if "unit_serial" in data and data["unit_serial"]:
            unit = self.normalize_unit_serial(data["unit_serial"])
            if unit:
                normalized["unit_serials"].add(unit)
                if unit != data["unit_serial"].strip().upper():
                    normalized["normalization_applied"].append(
                        f"Unit serial: '{data['unit_serial']}' → '{unit}'"
                    )
        
        # Normalize part numbers (with or without revisions)
        if "part_numbers" in data:
            # Handle both list of strings and list of dicts
            parts = data["part_numbers"]
            if isinstance(parts, list):
                for part in parts:
                    if isinstance(part, dict):
                        # PDF format: {"part": "PCA-1153-03", "revision": "F"}
                        # or Excel format: {"part_number": "PCA-1153-03", "revision": "E"}
                        part_num_raw = part.get("part_number") or part.get("part")
                        part_num = self.normalize_part_number(part_num_raw) if part_num_raw else None
                        revision = self.normalize_revision(part.get("revision", "")) if part.get("revision") else None
                        if part_num:
                            normalized["part_numbers"].add(part_num)
                            normalized["parts_with_revisions"].append({
                                "part_number": part_num,
                                "revision": revision
                            })
                    else:
                        # Just part number string
                        part_num = self.normalize_part_number(part)
                        if part_num:
                            normalized["part_numbers"].add(part_num)
                            normalized["parts_with_revisions"].append({
                                "part_number": part_num,
                                "revision": None
                            })
        
        # Normalize parts from BOM (has specific structure)
        if "parts" in data:
            for part in data["parts"]:
                part_num = self.normalize_part_number(part.get("part_number", ""))
                revision = self.normalize_revision(part.get("revision", "")) if part.get("revision") else None
                if part_num:
                    normalized["part_numbers"].add(part_num)
                    normalized["parts_with_revisions"].append({
                        "part_number": part_num,
                        "revision": revision
                    })
        
        # Convert sets to sorted lists for JSON serialization
        normalized["job_numbers"] = sorted(list(normalized["job_numbers"]))
        normalized["board_serials"] = sorted(list(normalized["board_serials"]))
        normalized["part_numbers"] = sorted(list(normalized["part_numbers"]))
        normalized["unit_serials"] = sorted(list(normalized["unit_serials"]))
        
        logger.info(f"[Normalizer] Normalized {source}: "
                   f"{len(normalized['job_numbers'])} jobs, "
                   f"{len(normalized['part_numbers'])} parts, "
                   f"{len(normalized['board_serials'])} boards, "
                   f"{len(normalized['unit_serials'])} units")
        
        if normalized["normalization_applied"]:
            logger.info(f"[Normalizer] Applied {len(normalized['normalization_applied'])} normalizations:")
            for norm in normalized["normalization_applied"][:5]:  # Show first 5
                logger.info(f"  - {norm}")
        
        return normalized


# Singleton instance
data_normalizer = DataNormalizer()

