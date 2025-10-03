# ocr_service.py
"""
OCR Service for Product Image Analysis with robust label extraction
"""

import logging
import re
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

import cv2
import numpy as np
import pytesseract

from app.config import settings

logger = logging.getLogger(__name__)

# ------------------------------ Regex Patterns ------------------------------
RE_UNIT_SERIAL = re.compile(r"\bINF-\d{4}\b")
RE_FLIGHT_STATUS = re.compile(r"\b(EDU\s*[-–]\s*NOT\s*FOR\s*FLIGHT|FLIGHT)\b", re.IGNORECASE)
RE_MODEL = re.compile(r"\b400XS\b")
RE_VOLTAGE = re.compile(r"\b(\d{2})V\b")
RE_DATE = re.compile(r"\b(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)\d{2}\b")
RE_CONNECTOR = re.compile(r"\bJX\d+\b")
RE_REV = re.compile(r"\bREV\s*[A-Z]\b", re.IGNORECASE)

# VGN patterns - lenient to handle OCR errors like "IVGN" or "1VGN"
RE_VGN_SERIAL = re.compile(r"[A-Z0-9]?VGN[-\s]*(\d{5})[-\s]*(\d{4})\b", re.IGNORECASE)

# PCA patterns
RE_PCA_STRICT = re.compile(r"\bPCA-(\d{4})-(\d{2})\b")
RE_PCA_LOOSE = re.compile(r"P[CG]A[-\s]*(\d{4})[-\s]*(\d{2})", re.IGNORECASE)

@dataclass
class ExtractionResult:
    unit_serial: Optional[str] = None
    flight_status: Optional[str] = None
    board_serials: List[str] = field(default_factory=list)
    part_numbers: List[str] = field(default_factory=list)
    revisions: List[str] = field(default_factory=list)
    model: Optional[str] = None
    voltage: Optional[str] = None
    date_code: Optional[str] = None
    connectors: List[str] = field(default_factory=list)
    raw_text_lid: str = ""
    raw_text_all: str = ""
    validations: Dict[str, bool] = field(default_factory=dict)

class HardwareImageExtractor:
    """OCR pipeline with enhanced white label processing"""
    
    def __init__(self, tesseract_cmd: Optional[str] = None):
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
            self._tess_bin = tesseract_cmd
        else:
            self._tess_bin = getattr(pytesseract.pytesseract, "tesseract_cmd", "tesseract")
    
    def analyze(self, image_path: str) -> ExtractionResult:
        logger.info("[OCR] Starting image analysis: %s", image_path)
        img_bgr = cv2.imread(image_path)
        if img_bgr is None:
            raise FileNotFoundError(f"Cannot read image: {image_path}")
        
        # Step 1-2: Preprocessing and lid detection
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        lid_roi, lid_bbox = self._find_black_lid(gray)
        
        # Step 3-5: OCR on different regions
        logger.info("[OCR] Processing lid, full image, and PCB regions...")
        lid_text = self._ocr_black_lid(lid_roi)
        full_text = self._ocr_full_image(gray)
        pcb_texts = self._ocr_pcb_tiles(gray)
        
        # Step 6: White label detection and OCR
        logger.info("[OCR] Detecting and processing white labels...")
        label_boards, label_parts, label_revisions, label_texts = self._process_white_labels(img_bgr, gray, lid_bbox)
        
        # Step 7: Parse and extract structured data
        logger.info("[OCR] Extracting structured data...")
        combined_text = "\n".join([full_text] + pcb_texts + label_texts)
        result = self._parse_all(lid_text, combined_text, label_boards, label_parts, label_revisions)
        
        # Validations
        result.validations["flight_status_ok"] = result.flight_status in {"FLIGHT", "EDU - NOT FOR FLIGHT"}
        result.validations["unit_serial_format_ok"] = bool(result.unit_serial and RE_UNIT_SERIAL.fullmatch(result.unit_serial))
        result.validations["has_VGN_80751_0053"] = "VGN-80751-0053" in result.board_serials
        
        return result
    
    def _find_black_lid(self, gray: np.ndarray) -> Tuple[np.ndarray, Tuple[int, int, int, int]]:
        """Find the black lid region in bottom-left"""
        h, w = gray.shape
        
        # Use adaptive threshold to find dark regions
        _, binary = cv2.threshold(gray, 80, 255, cv2.THRESH_BINARY_INV)
        
        # Find contours
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Look for rectangular dark region in bottom-left
        best_rect = None
        best_area = 0
        
        for cnt in contours:
            x, y, cw, ch = cv2.boundingRect(cnt)
            area = cw * ch
            
            # Check if it's in bottom-left quadrant and rectangular
            if (x < w * 0.5 and y > h * 0.4 and 
                area > 0.02 * w * h and area < 0.25 * w * h):
                aspect_ratio = cw / ch
                if 0.8 < aspect_ratio < 1.5:
                    if area > best_area:
                        best_area = area
                        best_rect = (x, y, cw, ch)
        
        if best_rect:
            x, y, cw, ch = best_rect
        else:
            # Fallback to bottom-left corner
            x, y = 0, int(h * 0.5)
            cw, ch = int(w * 0.5), int(h * 0.5)
        
        # Add padding
        pad = 20
        x0 = max(0, x - pad)
        y0 = max(0, y - pad)
        x1 = min(w, x + cw + pad)
        y1 = min(h, y + ch + pad)
        
        roi = gray[y0:y1, x0:x1]
        return roi, (x0, y0, x1, y1)
    
    def _ocr_black_lid(self, roi: np.ndarray) -> str:
        """OCR the black lid with special preprocessing"""
        # Invert for white text on black
        inverted = cv2.bitwise_not(roi)
        
        # Try with Tesseract directly using subprocess
        text = self._run_tesseract_subprocess(inverted, psm=6)
        return text
    
    def _ocr_full_image(self, gray: np.ndarray) -> str:
        """Quick OCR of downscaled full image"""
        h, w = gray.shape
        scale = min(1.0, 2000 / max(h, w))
        
        if scale < 1.0:
            resized = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
        else:
            resized = gray
        
        _, binary = cv2.threshold(resized, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return self._run_tesseract_subprocess(binary, psm=11)
    
    def _ocr_pcb_tiles(self, gray: np.ndarray) -> List[str]:
        """OCR specific PCB regions"""
        h, w = gray.shape
        tiles = [
            gray[0:int(h*0.5), 0:int(w*0.5)],      # Top-left
            gray[0:int(h*0.5), int(w*0.5):w],      # Top-right  
            gray[int(h*0.5):h, int(w*0.5):w],      # Bottom-right
        ]
        
        results = []
        for i, tile in enumerate(tiles):
            # Preprocess tile
            _, binary = cv2.threshold(tile, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            text = self._run_tesseract_subprocess(binary, psm=6)
            results.append(text)
        
        return results
    
    def _process_white_labels(self, img_bgr: np.ndarray, gray: np.ndarray, 
                             lid_bbox: Tuple[int, int, int, int]) -> Tuple[List[str], List[str], List[str], List[str]]:
        """Enhanced white label detection and OCR - returns (boards, parts, revisions, texts)"""
        h, w = gray.shape
        xL0, yL0, xL1, yL1 = lid_bbox
        
        # Detect white regions
        labels = self._detect_white_labels(img_bgr, (xL0, yL0, xL1, yL1))
        
        all_boards = []
        all_parts = []
        all_texts = []
        all_revisions = []
        
        for idx, (x, y, lw, lh) in enumerate(labels[:10], 1):
            # Extract label with padding
            pad = max(20, int(0.1 * max(lw, lh)))
            x0 = max(0, x - pad)
            y0 = max(0, y - pad)
            x1 = min(w, x + lw + pad)
            y1 = min(h, y + lh + pad)
            
            label_roi = gray[y0:y1, x0:x1]
            
            # Process this label
            text = self._ocr_single_label_robust(label_roi, idx)
            
            if text:
                all_texts.append(text)
                
                # Extract boards, parts, and revisions
                boards, parts, revs = self._extract_from_text(text)
                all_boards.extend(boards)
                all_parts.extend(parts)
                all_revisions.extend(revs)
        
        logger.info("[OCR] Found %d white labels with identifiers", len(all_texts))
        return all_boards, all_parts, all_revisions, all_texts
    
    def _detect_white_labels(self, img_bgr: np.ndarray, 
                             lid_bbox: Tuple[int, int, int, int]) -> List[Tuple[int, int, int, int]]:
        """Detect white label regions"""
        h, w = img_bgr.shape[:2]
        xL0, yL0, xL1, yL1 = lid_bbox
        
        # Convert to HSV
        hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
        
        # White detection: low saturation, high value
        lower_white = np.array([0, 0, 180])  # Adjusted for better detection
        upper_white = np.array([180, 80, 255])
        mask = cv2.inRange(hsv, lower_white, upper_white)
        
        # Morphology to clean up
        kernel = np.ones((3, 3), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        
        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        labels = []
        for cnt in contours:
            x, y, cw, ch = cv2.boundingRect(cnt)
            area = cw * ch
            
            # Filter by size
            if area < 200 or area > 0.05 * w * h:
                continue
                
            # Skip if overlaps with lid
            if x < xL1 and x + cw > xL0 and y < yL1 and y + ch > yL0:
                continue
            
            # Check aspect ratio (labels are usually rectangular)
            aspect = max(cw, ch) / min(cw, ch)
            if aspect < 1.2 or aspect > 15:
                continue
            
            labels.append((x, y, cw, ch))
        
        # Sort by area (larger labels first)
        labels.sort(key=lambda t: t[2] * t[3], reverse=True)
        
        return labels
    
    def _ocr_single_label_robust(self, roi: np.ndarray, label_idx: int) -> str:
        """Robust OCR for single white label with multi-rotation support"""
        return self._ocr_label_with_rotations(roi, label_idx)
    
    def _run_tesseract_subprocess(self, image: np.ndarray, psm: int = 6) -> str:
        """Run Tesseract using subprocess for more control"""
        # Save image to temp file
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            cv2.imwrite(tmp.name, image)
            tmp_path = tmp.name
        
        try:
            # Run tesseract with less restrictive settings
            cmd = [
                self._tess_bin,
                tmp_path,
                'stdout',
                '--oem', '1',
                '--psm', str(psm),
                '-l', 'eng'
            ]
            
            # Don't restrict characters for labels - we need all text
            if psm not in [7, 8]:  # Not for single line modes
                cmd.extend(['-c', 'tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789- '])
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            text = result.stdout.strip()
            
            # Clean up temp file
            Path(tmp_path).unlink()
            
            return text
            
        except Exception as e:
            logger.warning("[OCR] Tesseract subprocess failed: %s", e)
            # Clean up temp file
            if Path(tmp_path).exists():
                Path(tmp_path).unlink()
            return ""
    
    def _ocr_label_with_rotations(self, roi: np.ndarray, label_idx: int) -> str:
        """Try OCR with multiple rotations and preprocessing methods"""
        all_results = {}
        
        # Try 4 rotations: 0°, 90°, 180°, 270°
        rotations = [
            (0, roi, "0°"),
            (90, cv2.rotate(roi, cv2.ROTATE_90_CLOCKWISE), "90°"),
            (180, cv2.rotate(roi, cv2.ROTATE_180), "180°"),
            (270, cv2.rotate(roi, cv2.ROTATE_90_COUNTERCLOCKWISE), "270°")
        ]
        
        for angle, rotated_roi, angle_name in rotations:
            # Scale up if too small
            h, w = rotated_roi.shape
            if max(h, w) < 200:
                scale = 300 / max(h, w)
                rotated_roi = cv2.resize(rotated_roi, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
            
            # Try multiple preprocessing methods
            methods = []
            
            # Method 1: OTSU binary
            _, binary = cv2.threshold(rotated_roi, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            methods.append(("OTSU", binary))
            
            # Method 2: Inverted OTSU
            methods.append(("INV_OTSU", cv2.bitwise_not(binary)))
            
            # Method 3: Adaptive threshold
            adaptive = cv2.adaptiveThreshold(rotated_roi, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                            cv2.THRESH_BINARY, 21, 10)
            methods.append(("ADAPTIVE", adaptive))
            
            for method_name, processed in methods:
                # Try different PSM modes
                for psm in [6, 7, 8]:
                    text = self._run_tesseract_subprocess(processed, psm=psm)
                    if text and len(text) > 3:
                        key = f"{angle_name}_{method_name}_PSM{psm}"
                        all_results[key] = text
        
        # Find best result - prefer ones with PCA or VGN
        best_text = ""
        for key, text in all_results.items():
            text_up = text.upper()
            if "PCA" in text_up or "VGN" in text_up:
                if len(text) > len(best_text):
                    best_text = text
        
        # If no PCA/VGN found, return longest result
        if not best_text and all_results:
            best_text = max(all_results.values(), key=len)
        
        return best_text
    
    def _extract_from_text(self, text: str) -> Tuple[List[str], List[str], List[str]]:
        """Extract board serials, part numbers, and revisions from text"""
        if not text:
            return [], [], []
        
        text_up = text.upper()
        boards = []
        parts = []
        revisions = []
        
        # Extract VGN serials
        for match in RE_VGN_SERIAL.finditer(text_up):
            p1 = self._fix_digits(match.group(1))
            p2 = self._fix_digits(match.group(2))
            if p1.isdigit() and p2.isdigit():
                serial = f"VGN-{p1}-{p2}"
                boards.append(serial)
        
        # Extract PCA parts
        for match in RE_PCA_LOOSE.finditer(text_up):
            p1 = self._fix_digits(match.group(1))
            p2 = self._fix_digits(match.group(2))
            if p1.isdigit() and p2.isdigit():
                parts.append(f"PCA-{p1}-{p2}")
        
        # Extract revisions ONLY if this text contains PCA or VGN (i.e., it's a label)
        has_pca = "PCA" in text_up
        has_vgn = "VGN" in text_up
        
        if has_pca or has_vgn:
            # Pattern matches: "REV E", "REV C", "R F", "RE C", etc.
            rev_pattern = re.compile(r"\bR(?:EV?)?[^\w]*([A-Z])\b", re.IGNORECASE)
            for match in rev_pattern.finditer(text_up):
                rev_letter = match.group(1).upper()
                # Exclude common false positives (numbers misread as letters, etc.)
                if rev_letter not in ['I', 'O', 'N', 'S', 'G', 'A']:  # Common OCR noise
                    rev_str = f"REV {rev_letter}"
                    if rev_str not in revisions:
                        revisions.append(rev_str)
        
        return boards, parts, revisions
    
    def _fix_digits(self, s: str) -> str:
        """Fix common OCR digit errors"""
        return (s.replace("O", "0")
                 .replace("o", "0")
                 .replace("I", "1")
                 .replace("l", "1")
                 .replace("S", "5")
                 .replace("B", "8")
                 .replace("G", "6")
                 .replace("Z", "2"))
    
    def _parse_all(self, lid_text: str, combined_text: str,
                   label_boards: List[str], label_parts: List[str], 
                   label_revisions: List[str]) -> ExtractionResult:
        """Parse all extracted text"""
        lid_up = lid_text.upper()
        combined_up = combined_text.upper()
        
        result = ExtractionResult(raw_text_lid=lid_text, raw_text_all=combined_text)
        
        # Extract unit serial
        unit = RE_UNIT_SERIAL.search(lid_up) or RE_UNIT_SERIAL.search(combined_up)
        result.unit_serial = unit.group(0) if unit else None
        
        # Extract flight status
        fs = RE_FLIGHT_STATUS.search(lid_up) or RE_FLIGHT_STATUS.search(combined_up)
        if fs:
            val = fs.group(0).upper()
            result.flight_status = "EDU - NOT FOR FLIGHT" if "EDU" in val else "FLIGHT"
        
        # Extract other fields
        model = RE_MODEL.search(lid_up) or RE_MODEL.search(combined_up)
        result.model = model.group(0) if model else None
        
        volt = RE_VOLTAGE.search(combined_up)
        result.voltage = volt.group(0) if volt else None
        
        date = RE_DATE.search(combined_up)
        result.date_code = date.group(0) if date else None
        
        # Extract boards, parts, and revisions from all text
        all_boards, all_parts, all_revisions = self._extract_from_text(combined_text)
        
        # Combine with label results
        all_boards.extend(label_boards)
        all_parts.extend(label_parts)
        all_revisions.extend(label_revisions)
        
        # Deduplicate
        result.board_serials = list(dict.fromkeys(all_boards))
        result.part_numbers = list(dict.fromkeys(all_parts))
        result.revisions = list(dict.fromkeys(all_revisions))
        
        # Print formatted extraction summary
        logger.info("\n" + "=" * 80)
        logger.info("📋 IMAGE OCR EXTRACTION SUMMARY")
        logger.info("=" * 80)
        logger.info(f"🔢 Unit Serial:    {result.unit_serial or 'NOT FOUND'}")
        logger.info(f"✈️  Flight Status:  {result.flight_status or 'NOT FOUND'}")
        logger.info(f"📦 Model:          {result.model or 'NOT FOUND'}")
        logger.info(f"⚡ Voltage:        {result.voltage or 'NOT FOUND'}")
        logger.info(f"📅 Date Code:      {result.date_code or 'NOT FOUND'}")
        logger.info("-" * 80)
        logger.info(f"🔌 Board Serials ({len(result.board_serials)}):")
        for idx, board in enumerate(result.board_serials, 1):
            logger.info(f"   {idx}. {board}")
        logger.info("-" * 80)
        logger.info(f"🔧 Part Numbers ({len(result.part_numbers)}):")
        for idx, part in enumerate(result.part_numbers, 1):
            logger.info(f"   {idx}. {part}")
        logger.info("-" * 80)
        logger.info(f"📝 Revisions ({len(result.revisions)}):")
        for idx, rev in enumerate(result.revisions, 1):
            logger.info(f"   {idx}. {rev}")
        logger.info("-" * 80)
        logger.info(f"🔗 Connectors ({len(result.connectors)}):")
        logger.info(f"   {', '.join(result.connectors) if result.connectors else 'NONE'}")
        logger.info("=" * 80)
        
        return result

# ------------------------------ Facade --------------------------------------
class ProductImageOCR:
    def __init__(self):
        self.extractor = HardwareImageExtractor(settings.TESSERACT_CMD)
        logger.info("ProductImageOCR service initialized")
    
    def process_image(self, image_path: str) -> Dict[str, Any]:
        logger.info(f"[OCR] Pipeline start for {image_path}")
        
        if not Path(image_path).exists():
            raise FileNotFoundError(f"Image file not found: {image_path}")
        
        extraction = self.extractor.analyze(image_path)
        
        result: Dict[str, Any] = {
            "board_serials": extraction.board_serials,
            "part_numbers": [{"part_number": pn, "revision": pn[-2:]} for pn in extraction.part_numbers],
            "unit_serial": extraction.unit_serial,
            "flight_status": extraction.flight_status,
            "raw_text": extraction.raw_text_all,
            "preprocessing_methods": [
                "subprocess_tesseract", "multi_threshold", "adaptive_preprocessing",
                "rotation_attempts", "white_label_detection"
            ],
            "validation": {
                "completeness_score": 0.0,
                "validation_errors": [],
                "validation_warnings": [],
            },
            "metadata": {
                "image_path": image_path,
                "additional": {
                    "model": extraction.model,
                    "voltage": extraction.voltage,
                    "date_code": extraction.date_code,
                    "connectors": extraction.connectors,
                    "revisions": extraction.revisions,
                    "raw_text_lid": extraction.raw_text_lid,
                },
                "validations": extraction.validations,
            },
        }
        
        # Calculate completeness
        completeness = 0
        if extraction.board_serials: 
            completeness += 25
        else: 
            result["validation"]["validation_warnings"].append("Board serials missing")
        
        if extraction.part_numbers: 
            completeness += 25
        else: 
            result["validation"]["validation_warnings"].append("Part numbers missing")
        
        if extraction.unit_serial: 
            completeness += 25
        else: 
            result["validation"]["validation_warnings"].append("Unit serial missing")
        
        if extraction.flight_status: 
            completeness += 25
        else: 
            result["validation"]["validation_warnings"].append("Flight status missing")
        
        result["validation"]["completeness_score"] = completeness
        
        logger.info(
            "[OCR] Pipeline complete: %s board serials, %s part numbers, unit=%s, flight=%s",
            len(extraction.board_serials), len(extraction.part_numbers),
            extraction.unit_serial, extraction.flight_status
        )
        
        return result

# Singleton
ocr_service = ProductImageOCR()
