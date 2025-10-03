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
    """Single validation check result"""
    check_number: int
    check_name: str
    status: CheckStatus
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
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
        """
        check_num = 1
        check_name = "Job Number Match"
        
        if not traveler or not bom:
            self.checks.append(ValidationCheck(
                check_number=check_num,
                check_name=check_name,
                status=CheckStatus.FAIL,
                message="Missing traveler or BOM data",
                priority=1
            ))
            return
        
        traveler_jobs = set(traveler.get("job_numbers", []))
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
                priority=1
            ))
            return
        
        # Check if traveler job exists in BOM
        matching_jobs = traveler_jobs & bom_jobs
        
        if matching_jobs:
            self.checks.append(ValidationCheck(
                check_number=check_num,
                check_name=check_name,
                status=CheckStatus.PASS,
                message=f"Job {', '.join(matching_jobs)} found in BOM files",
                details={
                    "traveler_jobs": list(traveler_jobs),
                    "bom_jobs": list(bom_jobs),
                    "matching_jobs": list(matching_jobs)
                },
                priority=1
            ))
        else:
            self.checks.append(ValidationCheck(
                check_number=check_num,
                check_name=check_name,
                status=CheckStatus.FAIL,
                message=f"Job {', '.join(traveler_jobs)} not found in any BOM",
                details={
                    "traveler_jobs": list(traveler_jobs),
                    "bom_jobs": list(bom_jobs)
                },
                priority=1
            ))
    
    def _check_2_part_numbers_match(self, traveler: Optional[Dict], 
                                     image: Optional[Dict],
                                     bom: Optional[Dict]) -> None:
        """
        Check 2: Part Numbers Match (CRITICAL)
        Every part number from Traveler/Image must exist in BOM files.
        """
        check_num = 2
        check_name = "Part Numbers Match"
        
        if not bom:
            self.checks.append(ValidationCheck(
                check_number=check_num,
                check_name=check_name,
                status=CheckStatus.FAIL,
                message="No BOM data available",
                priority=1
            ))
            return
        
        # Collect all parts from traveler and image
        source_parts = set()
        if traveler:
            source_parts.update(traveler.get("part_numbers", []))
        if image:
            source_parts.update(image.get("part_numbers", []))
        
        bom_parts = set(bom.get("part_numbers", []))
        
        if not source_parts:
            self.checks.append(ValidationCheck(
                check_number=check_num,
                check_name=check_name,
                status=CheckStatus.WARNING,
                message="No part numbers found in traveler or image",
                priority=1
            ))
            return
        
        # Check which parts are in BOM
        found_parts = source_parts & bom_parts
        missing_parts = source_parts - bom_parts
        
        if not missing_parts:
            self.checks.append(ValidationCheck(
                check_number=check_num,
                check_name=check_name,
                status=CheckStatus.PASS,
                message=f"All {len(found_parts)} parts found in BOM",
                details={
                    "source_parts": sorted(list(source_parts)),
                    "found_in_bom": sorted(list(found_parts)),
                    "total_bom_parts": len(bom_parts)
                },
                priority=1
            ))
        else:
            self.checks.append(ValidationCheck(
                check_number=check_num,
                check_name=check_name,
                status=CheckStatus.FAIL,
                message=f"{len(missing_parts)} part(s) missing in BOM: {', '.join(sorted(missing_parts))}",
                details={
                    "source_parts": sorted(list(source_parts)),
                    "found_in_bom": sorted(list(found_parts)),
                    "missing_in_bom": sorted(list(missing_parts))
                },
                priority=1
            ))
    
    def _check_3_revisions_match(self, traveler: Optional[Dict],
                                  image: Optional[Dict],
                                  bom: Optional[Dict]) -> None:
        """
        Check 3: Revisions Match (MODERATE)
        Part revisions should match, with tolerance for format differences.
        """
        check_num = 3
        check_name = "Revisions Match"
        
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
                    # Keep track of all revisions for this part in BOM
                    if part_num not in bom_revs:
                        bom_revs[part_num] = set()
                    bom_revs[part_num].add(part["revision"])
        
        # Compare revisions
        mismatches = []
        matches = []
        
        # Check traveler vs BOM
        for part_num, traveler_rev in traveler_revs.items():
            if part_num in bom_revs:
                bom_rev_set = bom_revs[part_num]
                if traveler_rev in bom_rev_set:
                    matches.append(f"{part_num}: Rev {traveler_rev}")
                else:
                    mismatches.append(
                        f"{part_num}: Traveler Rev {traveler_rev} vs BOM Rev {', '.join(bom_rev_set)}"
                    )
        
        # Check image vs BOM
        for part_num, image_rev in image_revs.items():
            if part_num in bom_revs and part_num not in traveler_revs:
                bom_rev_set = bom_revs[part_num]
                if image_rev in bom_rev_set:
                    matches.append(f"{part_num}: Rev {image_rev}")
                else:
                    mismatches.append(
                        f"{part_num}: Image Rev {image_rev} vs BOM Rev {', '.join(bom_rev_set)}"
                    )
        
        if not traveler_revs and not image_revs:
            self.checks.append(ValidationCheck(
                check_number=check_num,
                check_name=check_name,
                status=CheckStatus.INFO,
                message="No revisions found in traveler or image to validate",
                priority=2
            ))
        elif not mismatches:
            self.checks.append(ValidationCheck(
                check_number=check_num,
                check_name=check_name,
                status=CheckStatus.PASS,
                message=f"All {len(matches)} revisions match",
                details={"matches": matches},
                priority=2
            ))
        else:
            self.checks.append(ValidationCheck(
                check_number=check_num,
                check_name=check_name,
                status=CheckStatus.WARNING,
                message=f"{len(mismatches)} revision mismatch(es) found",
                details={
                    "mismatches": mismatches,
                    "matches": matches
                },
                priority=2
            ))
    
    def _check_4_board_serials_match(self, traveler: Optional[Dict],
                                      image: Optional[Dict]) -> None:
        """
        Check 4: Board Serials Match (MODERATE)
        Board serials must match after normalization.
        """
        check_num = 4
        check_name = "Board Serials Match"
        
        if not traveler or not image:
            self.checks.append(ValidationCheck(
                check_number=check_num,
                check_name=check_name,
                status=CheckStatus.FAIL,
                message="Missing traveler or image data",
                priority=2
            ))
            return
        
        traveler_boards = set(traveler.get("board_serials", []))
        image_boards = set(image.get("board_serials", []))
        
        if not traveler_boards and not image_boards:
            self.checks.append(ValidationCheck(
                check_number=check_num,
                check_name=check_name,
                status=CheckStatus.WARNING,
                message="No board serials found in traveler or image",
                priority=2
            ))
            return
        
        matching_boards = traveler_boards & image_boards
        traveler_only = traveler_boards - image_boards
        image_only = image_boards - traveler_boards
        
        # Check if normalization was applied
        normalized = (traveler.get("normalization_applied") or 
                     image.get("normalization_applied"))
        
        if traveler_boards == image_boards:
            msg = f"All {len(matching_boards)} board serials match"
            if normalized:
                msg += " (after normalization)"
            
            status = CheckStatus.INFO if normalized else CheckStatus.PASS
            
            self.checks.append(ValidationCheck(
                check_number=check_num,
                check_name=check_name,
                status=status,
                message=msg,
                details={
                    "matching_boards": sorted(list(matching_boards)),
                    "normalized": bool(normalized)
                },
                priority=2
            ))
        else:
            mismatches = []
            if traveler_only:
                mismatches.append(f"In traveler only: {', '.join(sorted(traveler_only))}")
            if image_only:
                mismatches.append(f"In image only: {', '.join(sorted(image_only))}")
            
            self.checks.append(ValidationCheck(
                check_number=check_num,
                check_name=check_name,
                status=CheckStatus.FAIL,
                message=f"Board serial mismatch: {len(matching_boards)} match, {len(traveler_only + image_only)} differ",
                details={
                    "matching": sorted(list(matching_boards)),
                    "traveler_only": sorted(list(traveler_only)),
                    "image_only": sorted(list(image_only))
                },
                priority=2
            ))
    
    def _check_5_unit_serial_match(self, traveler: Optional[Dict],
                                    image: Optional[Dict]) -> None:
        """
        Check 5: Unit Serial Match (MODERATE)
        Unit serial must match after normalization.
        """
        check_num = 5
        check_name = "Unit Serial Match"
        
        if not traveler or not image:
            self.checks.append(ValidationCheck(
                check_number=check_num,
                check_name=check_name,
                status=CheckStatus.FAIL,
                message="Missing traveler or image data",
                priority=2
            ))
            return
        
        traveler_units = set(traveler.get("unit_serials", []))
        image_units = set(image.get("unit_serials", []))
        
        if not traveler_units and not image_units:
            self.checks.append(ValidationCheck(
                check_number=check_num,
                check_name=check_name,
                status=CheckStatus.WARNING,
                message="No unit serials found in traveler or image",
                priority=2
            ))
            return
        
        matching_units = traveler_units & image_units
        
        # Check if normalization was applied
        normalized = (traveler.get("normalization_applied") or 
                     image.get("normalization_applied"))
        
        if matching_units:
            msg = f"Unit serial {', '.join(matching_units)} matches"
            if normalized:
                msg += " (after normalization)"
            
            status = CheckStatus.INFO if normalized else CheckStatus.PASS
            
            self.checks.append(ValidationCheck(
                check_number=check_num,
                check_name=check_name,
                status=status,
                message=msg,
                details={
                    "unit_serial": list(matching_units)[0] if matching_units else None,
                    "normalized": bool(normalized)
                },
                priority=2
            ))
        else:
            self.checks.append(ValidationCheck(
                check_number=check_num,
                check_name=check_name,
                status=CheckStatus.FAIL,
                message=f"Unit serial mismatch: Traveler={', '.join(traveler_units) if traveler_units else 'None'}, Image={', '.join(image_units) if image_units else 'None'}",
                details={
                    "traveler_units": list(traveler_units),
                    "image_units": list(image_units)
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

