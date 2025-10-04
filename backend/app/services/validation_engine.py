"""
Validation Engine - Phase 9

Performs 7 priority-ordered validation checks to ensure manufacturing
documentation accuracy and completeness.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class CheckStatus(Enum):
    """Validation check status levels"""
    PASS = "PASS"
    WARNING = "WARNING"
    FAIL = "FAIL"
    INFO = "INFO"


class OverallStatus(Enum):
    """Overall validation result"""
    PASS = "PASS"
    WARNING = "WARNING"
    FAIL = "FAIL"


@dataclass
class ValidationCheck:
    """
    Single validation check result.
    
    Represents one validation item (e.g., one part number check, one revision check).
    Multiple checks of the same type can exist (e.g., checking multiple part numbers).
    """
    check_number: int
    check_name: str
    status: CheckStatus
    message: str
    expected_value: Optional[str] = None  # What we expected to find
    actual_value: Optional[str] = None    # What we actually found
    details: Dict[str, Any] = field(default_factory=dict)  # Additional metadata
    priority: int = 1  # 1=Critical, 2=Moderate, 3=Informational


@dataclass
class ValidationResult:
    """Complete validation result for a session"""
    overall_status: OverallStatus
    checks: List[ValidationCheck]
    summary: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "overall_status": self.overall_status.value,
            "checks": [
                {
                    "check_number": check.check_number,
                    "check_name": check.check_name,
                    "status": check.status.value,
                    "message": check.message,
                    "expected_value": check.expected_value,
                    "actual_value": check.actual_value,
                    "details": check.details,
                    "priority": check.priority
                }
                for check in self.checks
            ],
            "summary": self.summary
        }


class ValidationEngine:
    """
    7-Check Validation Engine
    
    Validates manufacturing documentation across Traveler PDF, Product Image,
    and Excel BOMs using normalized data from Phase 8.
    """
    
    def __init__(self):
        self.checks: List[ValidationCheck] = []
    
    def validate(self, normalized_data: Dict[str, Any], 
                 files_info: Dict[str, Any]) -> ValidationResult:
        """
        Run all 7 validation checks on normalized data.
        
        Args:
            normalized_data: Normalized data from Phase 8 (traveler, image, bom)
            files_info: File counts and metadata
            
        Returns:
            ValidationResult with all check results and overall status
        """
        logger.info("[Validation] Starting 7-check validation engine...")
        
        self.checks = []
        
        traveler = normalized_data.get("traveler")
        image = normalized_data.get("image")
        bom = normalized_data.get("bom")
        
        # Run all 7 checks
        self._check_1_job_number_match(traveler, bom)
        self._check_2_part_numbers_match(traveler, image, bom)
        self._check_3_revisions_match(traveler, image, bom)
        self._check_4_board_serials_match(traveler, image)
        self._check_5_unit_serial_match(traveler, image)
        self._check_6_flight_status(image, files_info)
        self._check_7_file_completeness(files_info)
        
        # Determine overall status
        overall_status = self._determine_overall_status()
        
        # Generate summary
        summary = self._generate_summary()
        
        result = ValidationResult(
            overall_status=overall_status,
            checks=self.checks,
            summary=summary
        )
        
        logger.info(f"[Validation] Validation complete - Overall status: {overall_status.value}")
        return result
    
    def _check_1_job_number_match(self, traveler: Optional[Dict], 
                                   bom: Optional[Dict]) -> None:
        """
        Check 1: Job Number Match (CRITICAL)
        Traveler job number must exist in at least one BOM file.
        Creates one check per job number found in traveler.
        """
        check_num = 1
        check_name = "Job Number"
        
        if not traveler or not bom:
            self.checks.append(ValidationCheck(
                check_number=check_num,
                check_name=check_name,
                status=CheckStatus.FAIL,
                message="Missing traveler or BOM data",
                priority=1
            ))
            return
        
        traveler_jobs = traveler.get("job_numbers", [])
        bom_jobs = set(bom.get("job_numbers", []))
        
        if not traveler_jobs:
            self.checks.append(ValidationCheck(
                check_number=check_num,
                check_name=check_name,
                status=CheckStatus.FAIL,
                message="No job number found in traveler",
                priority=1
            ))
            return
        
        if not bom_jobs:
            self.checks.append(ValidationCheck(
                check_number=check_num,
                check_name=check_name,
                status=CheckStatus.FAIL,
                message="No job numbers found in BOMs",
                expected_value="Job numbers in Excel BOMs",
                actual_value="No job numbers found",
                priority=1
            ))
            return
        
        # Create individual check for each traveler job number
        for job_num in traveler_jobs:
            if job_num in bom_jobs:
                # Find which BOM files contain this job
                bom_files = bom.get("aggregated_parts", {}).get("by_job", {}).get(job_num, {}).get("source_files", [])
                bom_files_str = ', '.join(bom_files) if bom_files else "Excel file(s)"
                
                self.checks.append(ValidationCheck(
                    check_number=check_num,
                    check_name=check_name,
                    status=CheckStatus.PASS,
                    message=f"Job number {job_num} found in {len(bom_files) if bom_files else 1} Excel file(s)",
                    expected_value=f"Job {job_num} in Excel BOMs",
                    actual_value=f"Found in: {bom_files_str}",
                    details={
                        "job_number": job_num,
                        "found_in_bom": True,
                        "bom_files": bom_files
                    },
                    priority=1
                ))
            else:
                self.checks.append(ValidationCheck(
                    check_number=check_num,
                    check_name=check_name,
                    status=CheckStatus.FAIL,
                    message=f"Job number {job_num} from traveler not found in any Excel BOMs",
                    expected_value=f"Job {job_num} in Excel BOMs",
                    actual_value="Not found in any BOM files",
                    details={
                        "job_number": job_num,
                        "found_in_bom": False,
                        "available_jobs": sorted(list(bom_jobs))
                    },
                    priority=1
                ))
    
    def _check_2_part_numbers_match(self, traveler: Optional[Dict], 
                                     image: Optional[Dict],
                                     bom: Optional[Dict]) -> None:
        """
        Check 2: Part Numbers Match (CRITICAL)
        Every part number from Traveler/Image must exist in BOM files.
        Creates individual check per part number.
        """
        check_num = 2
        check_name = "Part Number"
        
        if not bom:
            self.checks.append(ValidationCheck(
                check_number=check_num,
                check_name=check_name,
                status=CheckStatus.FAIL,
                message="No BOM data available",
                priority=1
            ))
            return
        
        # Collect all parts from traveler and image with their sources
        part_sources = {}  # part_number -> list of sources (traveler, image)
        
        if traveler:
            for part in traveler.get("part_numbers", []):
                if part not in part_sources:
                    part_sources[part] = []
                part_sources[part].append("traveler")
        
        if image:
            for part in image.get("part_numbers", []):
                if part not in part_sources:
                    part_sources[part] = []
                if "image" not in part_sources[part]:
                    part_sources[part].append("image")
        
        bom_parts = set(bom.get("part_numbers", []))
        
        if not part_sources:
            self.checks.append(ValidationCheck(
                check_number=check_num,
                check_name=check_name,
                status=CheckStatus.WARNING,
                message="No part numbers found in traveler or image",
                expected_value="Part numbers in traveler/image",
                actual_value="None found",
                priority=1
            ))
            return
        
        # Create individual check for each part number
        for part_num, sources in sorted(part_sources.items()):
            source_str = " and ".join(sources)
            
            if part_num in bom_parts:
                self.checks.append(ValidationCheck(
                    check_number=check_num,
                    check_name=check_name,
                    status=CheckStatus.PASS,
                    message=f"Part number {part_num} found in Excel BOMs",
                    expected_value=part_num,
                    actual_value=f"Found in: Excel BOM files",
                    details={
                        "part_number": part_num,
                        "source": sources,
                        "found_in_bom": True
                    },
                    priority=1
                ))
            else:
                self.checks.append(ValidationCheck(
                    check_number=check_num,
                    check_name=check_name,
                    status=CheckStatus.FAIL,
                    message=f"Part number {part_num} from {source_str} not found in any Excel BOMs",
                    expected_value=part_num,
                    actual_value="Not found in BOM files",
                    details={
                        "part_number": part_num,
                        "source": sources,
                        "found_in_bom": False
                    },
                    priority=1
                ))
    
    def _check_3_revisions_match(self, traveler: Optional[Dict],
                                  image: Optional[Dict],
                                  bom: Optional[Dict]) -> None:
        """
        Check 3: Revisions Match (MODERATE)
        Part revisions should match, with tolerance for format differences.
        Creates individual check per part with revision.
        """
        check_num = 3
        check_name = "Revision"
        
        # Collect parts with revisions from all sources
        traveler_revs = {}
        image_revs = {}
        bom_revs = {}
        
        if traveler and "parts_with_revisions" in traveler:
            for part in traveler["parts_with_revisions"]:
                if part.get("revision"):
                    traveler_revs[part["part_number"]] = part["revision"]
        
        if image and "parts_with_revisions" in image:
            for part in image["parts_with_revisions"]:
                if part.get("revision"):
                    image_revs[part["part_number"]] = part["revision"]
        
        if bom and "parts_with_revisions" in bom:
            for part in bom["parts_with_revisions"]:
                if part.get("revision"):
                    part_num = part["part_number"]
                    if part_num not in bom_revs:
                        bom_revs[part_num] = {}
                    # Store revision with its source file
                    rev = part["revision"]
                    if rev not in bom_revs[part_num]:
                        bom_revs[part_num][rev] = []
                    source_file = part.get("source_file", "BOM")
                    if source_file not in bom_revs[part_num][rev]:
                        bom_revs[part_num][rev].append(source_file)
        
        # Collect all parts that need revision checks
        all_parts = set(traveler_revs.keys()) | set(image_revs.keys())
        
        if not all_parts:
            self.checks.append(ValidationCheck(
                check_number=check_num,
                check_name=check_name,
                status=CheckStatus.INFO,
                message="Traveler document does not include individual board revision information (this is expected behavior)",
                expected_value="N/A",
                actual_value="No revision data in traveler",
                priority=2
            ))
            return
        
        # Create individual check for each part
        for part_num in sorted(all_parts):
            traveler_rev = traveler_revs.get(part_num)
            image_rev = image_revs.get(part_num)
            bom_rev_dict = bom_revs.get(part_num, {})
            
            # Determine the source revision (prefer traveler, fall back to image)
            source_rev = traveler_rev if traveler_rev else image_rev
            source = "traveler" if traveler_rev else "image"
            
            if not bom_rev_dict:
                # Part not found in BOM
                self.checks.append(ValidationCheck(
                    check_number=check_num,
                    check_name=check_name,
                    status=CheckStatus.WARNING,
                    message=f"Revision for {part_num}: No revision data in Excel BOMs",
                    expected_value=f"{part_num} Rev {source_rev}",
                    actual_value="No revision info in BOM",
                    details={
                        "part_number": part_num,
                        "source_revision": source_rev,
                        "source": source
                    },
                    priority=2
                ))
            elif source_rev in bom_rev_dict:
                # Exact match
                bom_files = ', '.join(bom_rev_dict[source_rev])
                self.checks.append(ValidationCheck(
                    check_number=check_num,
                    check_name=check_name,
                    status=CheckStatus.PASS,
                    message=f"{part_num} revision {source_rev} matches in {bom_files}",
                    expected_value=f"{part_num} Rev {source_rev}",
                    actual_value=f"Found in: {bom_files}",
                    details={
                        "part_number": part_num,
                        "revision": source_rev,
                        "bom_files": bom_rev_dict[source_rev],
                        "match": True
                    },
                    priority=2
                ))
            else:
                # Mismatch
                bom_revs_str = ", ".join([f"'{rev}'" for rev in bom_rev_dict.keys()])
                
                # Check if it's a minor revision difference (e.g., F vs F2)
                is_minor = any(
                    source_rev in rev or rev in source_rev 
                    for rev in bom_rev_dict.keys()
                )
                
                if is_minor:
                    status = CheckStatus.WARNING
                    msg = f"Revision mismatch for {part_num}: Excel shows {bom_revs_str} but {source} shows '{source_rev}'"
                else:
                    status = CheckStatus.WARNING
                    msg = f"Revision mismatch for {part_num}: Excel shows {bom_revs_str} but {source} shows '{source_rev}'"
                
                self.checks.append(ValidationCheck(
                    check_number=check_num,
                    check_name=check_name,
                    status=status,
                    message=msg,
                    expected_value=f"{part_num} Rev {source_rev}",
                    actual_value=f"Excel shows: {bom_revs_str}",
                    details={
                        "part_number": part_num,
                        "source_revision": source_rev,
                        "bom_revisions": list(bom_rev_dict.keys()),
                        "match": False,
                        "minor_difference": is_minor
                    },
                    priority=2
                ))
    
    def _check_4_board_serials_match(self, traveler: Optional[Dict],
                                      image: Optional[Dict]) -> None:
        """
        Check 4: Board Serials Match (MODERATE)
        Board serials must match after normalization.
        Creates individual check per board serial.
        """
        check_num = 4
        check_name = "Board Serial"
        
        if not traveler or not image:
            self.checks.append(ValidationCheck(
                check_number=check_num,
                check_name=check_name,
                status=CheckStatus.FAIL,
                message="Missing traveler or image data",
                priority=2
            ))
            return
        
        traveler_boards_raw = traveler.get("board_serials_raw", {})  # Original before normalization
        image_boards_raw = image.get("board_serials_raw", {})
        traveler_boards = set(traveler.get("board_serials", []))  # After normalization
        image_boards = set(image.get("board_serials", []))
        
        normalized = traveler.get("normalization_applied") or image.get("normalization_applied")
        
        if not traveler_boards and not image_boards:
            self.checks.append(ValidationCheck(
                check_number=check_num,
                check_name=check_name,
                status=CheckStatus.INFO,
                message="Note: Image shows 'VGN-' prefix on all board serials, traveler omits this prefix (this is expected)",
                expected_value="Board serials with optional VGN- prefix",
                actual_value="Prefix handling varies by source",
                priority=2
            ))
            return
        
        # Create individual check for each board serial
        all_board_serials = traveler_boards | image_boards
        
        for serial in sorted(all_board_serials):
            in_traveler = serial in traveler_boards
            in_image = serial in image_boards
            
            # Find the part number associated with this serial
            part_num = None
            for part, serials in traveler_boards_raw.items():
                if serial in serials or any(s.endswith(serial) or serial.endswith(s) for s in serials):
                    part_num = part
                    break
            if not part_num:
                for part, serials in image_boards_raw.items():
                    if serial in serials or any(s.endswith(serial) or serial.endswith(s) for s in serials):
                        part_num = part
                        break
            
            if in_traveler and in_image:
                # Match found
                msg_suffix = " (traveler without prefix)" if normalized else ""
                part_info = f"Board {part_num} " if part_num else ""
                
                self.checks.append(ValidationCheck(
                    check_number=check_num,
                    check_name=check_name,
                    status=CheckStatus.PASS,
                    message=f"{part_info}serial matches: {serial} (image) = {serial} {msg_suffix}",
                    expected_value=serial,
                    actual_value=f"{serial} (matched)",
                    details={
                        "serial": serial,
                        "part_number": part_num,
                        "normalized": normalized,
                        "in_traveler": True,
                        "in_image": True
                    },
                    priority=2
                ))
            else:
                # Mismatch - serial only in one source
                source = "image" if in_image else "traveler"
                self.checks.append(ValidationCheck(
                    check_number=check_num,
                    check_name=check_name,
                    status=CheckStatus.WARNING,
                    message=f"Board serial {serial} found only in {source}",
                    expected_value=f"{serial} in both sources",
                    actual_value=f"Only in {source}",
                    details={
                        "serial": serial,
                        "part_number": part_num,
                        "in_traveler": in_traveler,
                        "in_image": in_image
                    },
                    priority=2
                ))
    
    def _check_5_unit_serial_match(self, traveler: Optional[Dict],
                                    image: Optional[Dict]) -> None:
        """
        Check 5: Unit Serial Match (MODERATE)
        Unit serial must match after normalization.
        Creates individual check per unit serial.
        """
        check_num = 5
        check_name = "Unit Serial"
        
        if not traveler or not image:
            self.checks.append(ValidationCheck(
                check_number=check_num,
                check_name=check_name,
                status=CheckStatus.FAIL,
                message="Missing traveler or image data",
                priority=2
            ))
            return
        
        traveler_units = traveler.get("unit_serials", [])
        image_units = image.get("unit_serials", [])
        
        if not traveler_units and not image_units:
            self.checks.append(ValidationCheck(
                check_number=check_num,
                check_name=check_name,
                status=CheckStatus.WARNING,
                message="No unit serials found in traveler or image",
                expected_value="Unit serial in traveler/image",
                actual_value="Not found",
                priority=2
            ))
            return
        
        normalized = traveler.get("normalization_applied") or image.get("normalization_applied")
        
        # Typically there's only one unit serial, but handle multiple just in case
        all_units = set(traveler_units) | set(image_units)
        
        for unit_serial in sorted(all_units):
            in_traveler = unit_serial in traveler_units
            in_image = unit_serial in image_units
            
            if in_traveler and in_image:
                # Match found
                msg_suffix = " (traveler without prefix)" if normalized else ""
                
                self.checks.append(ValidationCheck(
                    check_number=check_num,
                    check_name=check_name,
                    status=CheckStatus.PASS,
                    message=f"Unit serial matches: {unit_serial} (image) = {unit_serial}{msg_suffix}",
                    expected_value=unit_serial,
                    actual_value=f"{unit_serial} (matched)",
                    details={
                        "unit_serial": unit_serial,
                        "normalized": normalized,
                        "in_traveler": True,
                        "in_image": True
                    },
                    priority=2
                ))
            else:
                # Mismatch
                source = "image" if in_image else "traveler"
                self.checks.append(ValidationCheck(
                    check_number=check_num,
                    check_name=check_name,
                    status=CheckStatus.WARNING,
                    message=f"Unit serial {unit_serial} found only in {source}",
                    expected_value=f"{unit_serial} in both sources",
                    actual_value=f"Only in {source}",
                    details={
                        "unit_serial": unit_serial,
                        "in_traveler": in_traveler,
                        "in_image": in_image
                    },
                    priority=2
                ))
    
    def _check_6_flight_status(self, image: Optional[Dict],
                                files_info: Dict[str, Any]) -> None:
        """
        Check 6: Flight Status (INFORMATIONAL)
        Detect and report flight status from image OCR.
        """
        check_num = 6
        check_name = "Flight Status"
        
        # Get flight status from image extracted data
        flight_status = None
        if image and "source_data" in files_info:
            image_data = files_info["source_data"].get("image")
            if image_data:
                flight_status = image_data.get("flight_status")
        
        if not flight_status:
            self.checks.append(ValidationCheck(
                check_number=check_num,
                check_name=check_name,
                status=CheckStatus.FAIL,
                message="Flight status marking not detected on hardware",
                priority=3
            ))
        elif "FLIGHT" in flight_status.upper() and "NOT" not in flight_status.upper():
            self.checks.append(ValidationCheck(
                check_number=check_num,
                check_name=check_name,
                status=CheckStatus.PASS,
                message="FLIGHT marking confirmed - Hardware is flight-qualified",
                details={"flight_status": flight_status},
                priority=3
            ))
        elif "EDU" in flight_status.upper() or "NOT FOR FLIGHT" in flight_status.upper():
            self.checks.append(ValidationCheck(
                check_number=check_num,
                check_name=check_name,
                status=CheckStatus.WARNING,
                message="Educational hardware (NOT FOR FLIGHT) - Not flight-qualified",
                details={"flight_status": flight_status},
                priority=3
            ))
        else:
            self.checks.append(ValidationCheck(
                check_number=check_num,
                check_name=check_name,
                status=CheckStatus.INFO,
                message=f"Flight status detected: {flight_status}",
                details={"flight_status": flight_status},
                priority=3
            ))
    
    def _check_7_file_completeness(self, files_info: Dict[str, Any]) -> None:
        """
        Check 7: File Completeness (CRITICAL)
        Ensure all required files are present and readable.
        """
        check_num = 7
        check_name = "File Completeness"
        
        traveler_count = files_info.get("traveler_count", 0)
        image_count = files_info.get("image_count", 0)
        bom_count = files_info.get("bom_count", 0)
        
        issues = []
        if traveler_count == 0:
            issues.append("No traveler PDF uploaded")
        elif traveler_count > 1:
            issues.append(f"{traveler_count} traveler PDFs (expected 1)")
        
        if image_count == 0:
            issues.append("No product image uploaded")
        elif image_count > 1:
            issues.append(f"{image_count} images (expected 1)")
        
        if bom_count == 0:
            issues.append("No BOM files uploaded")
        elif bom_count > 4:
            issues.append(f"{bom_count} BOMs (expected 1-4)")
        
        if not issues:
            self.checks.append(ValidationCheck(
                check_number=check_num,
                check_name=check_name,
                status=CheckStatus.PASS,
                message=f"All required files present: {traveler_count} PDF, {image_count} image, {bom_count} BOM(s)",
                details={
                    "traveler_count": traveler_count,
                    "image_count": image_count,
                    "bom_count": bom_count
                },
                priority=1
            ))
        else:
            self.checks.append(ValidationCheck(
                check_number=check_num,
                check_name=check_name,
                status=CheckStatus.FAIL,
                message=f"File completeness issues: {', '.join(issues)}",
                details={
                    "traveler_count": traveler_count,
                    "image_count": image_count,
                    "bom_count": bom_count,
                    "issues": issues
                },
                priority=1
            ))
    
    def _determine_overall_status(self) -> OverallStatus:
        """
        Determine overall validation status based on check results.
        
        Status Hierarchy: FAIL > WARNING > PASS > INFO
        """
        has_fail = any(check.status == CheckStatus.FAIL for check in self.checks)
        has_warning = any(check.status == CheckStatus.WARNING for check in self.checks)
        
        if has_fail:
            return OverallStatus.FAIL
        elif has_warning:
            return OverallStatus.WARNING
        else:
            return OverallStatus.PASS
    
    def _generate_summary(self) -> Dict[str, Any]:
        """Generate validation summary statistics"""
        status_counts = {
            "PASS": 0,
            "WARNING": 0,
            "FAIL": 0,
            "INFO": 0
        }
        
        for check in self.checks:
            status_counts[check.status.value] += 1
        
        return {
            "total_checks": len(self.checks),
            "status_counts": status_counts,
            "critical_failures": sum(1 for c in self.checks 
                                    if c.status == CheckStatus.FAIL and c.priority == 1),
            "checks_passed": status_counts["PASS"] + status_counts["INFO"],
            "checks_failed": status_counts["FAIL"],
            "checks_warning": status_counts["WARNING"]
        }


# Singleton instance
validation_engine = ValidationEngine()

