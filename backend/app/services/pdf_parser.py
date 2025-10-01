# app/services/pdf_parser.py
import pdfplumber
from typing import Dict, Any, List, Optional
from pathlib import Path
import logging

# Configure logging
logger = logging.getLogger(__name__)

class TravelerPDFParser:
    """
    Traveler PDF Parser Service
    
    Extracts structured data from manufacturing traveler PDFs including:
    - Job numbers (5 digits)
    - Work instructions (DRW-XXXX-YY format)  
    - Seq 20 section data (unit serials, board serials)
    - Part numbers with revisions
    """
    
    def __init__(self):
        """Initialize the PDF parser service"""
        self.logger = logging.getLogger(__name__)
    
    def parse_traveler_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """
        Parse a traveler PDF file and extract manufacturing data
        
        Args:
            pdf_path (str): Path to the traveler PDF file
            
        Returns:
            Dict[str, Any]: Extracted data structure:
            {
                "job_number": "82334",
                "work_instruction": "DRW-1608-03",
                "unit_serial": "1619", 
                "board_serials": ["80751-0053", "80641-0022"],
                "part_numbers": [
                    {"part": "PCA-1153-03", "revision": "F"},
                    {"part": "PCA-1052-05", "revision": "B"}
                ],
                "seq_20_data": {...},
                "parsing_status": "success",
                "errors": []
            }
            
        Raises:
            FileNotFoundError: If PDF file doesn't exist
            Exception: For PDF parsing errors
        """
        
        # Initialize result structure
        result = {
            "job_number": None,
            "work_instruction": None,
            "unit_serial": None,
            "board_serials": [],
            "part_numbers": [],
            "seq_20_data": {},
            "raw_text": "",
            "page_texts": [],
            "pdf_info": {},
            "tables": [],
            "validation": {},
            "parsing_status": "pending",
            "errors": []
        }
        
        try:
            # Validate file exists
            if not Path(pdf_path).exists():
                raise FileNotFoundError(f"PDF file not found: {pdf_path}")
            
            self.logger.info(f"Starting PDF parsing for: {pdf_path}")
            
            # Open PDF file with pdfplumber
            with pdfplumber.open(pdf_path) as pdf:
                # Extract basic PDF information
                pdf_info = {
                    "total_pages": len(pdf.pages),
                    "metadata": pdf.metadata if pdf.metadata else {}
                }
                
                # Extract text and tables from all pages
                all_text = ""
                page_texts = []
                all_tables = []
                
                for page_num, page in enumerate(pdf.pages, 1):
                    try:
                        # Extract text from current page
                        page_text = page.extract_text()
                        
                        if page_text:
                            page_texts.append({
                                "page_number": page_num,
                                "text": page_text.strip(),
                                "char_count": len(page_text.strip())
                            })
                            
                            # Add to combined text with page separator
                            all_text += f"\n--- PAGE {page_num} ---\n"
                            all_text += page_text.strip()
                            all_text += "\n"
                        else:
                            self.logger.warning(f"No text found on page {page_num}")
                        
                        # Extract tables from current page
                        try:
                            tables = page.extract_tables()
                            if tables:
                                for table_idx, table in enumerate(tables):
                                    if table:  # Ensure table has content
                                        all_tables.append({
                                            "page_number": page_num,
                                            "table_index": table_idx,
                                            "table_data": table,
                                            "row_count": len(table),
                                            "col_count": len(table[0]) if table else 0
                                        })
                                        
                                self.logger.info(f"Found {len(tables)} tables on page {page_num}")
                        except Exception as table_error:
                            self.logger.warning(f"Error extracting tables from page {page_num}: {str(table_error)}")
                            
                    except Exception as page_error:
                        error_msg = f"Error extracting text from page {page_num}: {str(page_error)}"
                        self.logger.warning(error_msg)
                        result["errors"].append(error_msg)
                
                # Store extracted text and table data
                result["raw_text"] = all_text.strip()
                result["page_texts"] = page_texts
                result["pdf_info"] = pdf_info
                result["tables"] = all_tables
                
                # Find and extract Seq 20 section data
                seq_20_data = self._find_seq_20_section(all_text, all_tables)
                result["seq_20_data"] = seq_20_data
                
                # Extract unit serial and board serials from Seq 20 data
                if seq_20_data and seq_20_data.get("found"):
                    result["unit_serial"] = seq_20_data.get("unit_serial")
                    result["board_serials"] = seq_20_data.get("board_serials", [])
                
                # Extract job number and work instruction from text
                result["job_number"] = self._extract_job_number(all_text)
                result["work_instruction"] = self._extract_work_instruction(all_text)
                
                # Extract part numbers with revisions
                result["part_numbers"] = self._extract_part_numbers(all_text)
                
                # Basic validation of extracted content
                if not all_text.strip():
                    raise Exception("No text could be extracted from PDF - file may be image-based or corrupted")
                
                if len(page_texts) == 0:
                    raise Exception("No readable pages found in PDF")
                
                # Validate extracted data quality and format
                validation_result = self._validate_extracted_data(result)
                result["validation"] = validation_result
                
                # Add warnings for missing critical data
                if not result["job_number"]:
                    result["errors"].append("Warning: Job number not found in PDF")
                
                if not result["work_instruction"]:
                    result["errors"].append("Warning: Work instruction not found in PDF")
                
                if not seq_20_data.get("found"):
                    result["errors"].append("Warning: Seq 20 section not found - unit/board serials may be incomplete")
                
                # Log extraction statistics
                total_chars = sum(page["char_count"] for page in page_texts)
                table_count = len(all_tables)
                self.logger.info(f"PDF extraction completed: {len(page_texts)} pages, {total_chars} characters, {table_count} tables")
                
                result["parsing_status"] = "success"
                
            return result
            
        except FileNotFoundError as e:
            error_msg = str(e)
            self.logger.error(f"File not found: {error_msg}")
            result["parsing_status"] = "failed"
            result["errors"].append(f"File error: {error_msg}")
            return result
            
        except PermissionError as e:
            error_msg = f"Permission denied accessing PDF file: {str(e)}"
            self.logger.error(error_msg)
            result["parsing_status"] = "failed"
            result["errors"].append(f"Permission error: {error_msg}")
            return result
            
        except Exception as e:
            # Handle common PDF-specific errors
            error_str = str(e).lower()
            
            if "password" in error_str or "encrypted" in error_str:
                error_msg = "PDF is password-protected or encrypted - cannot extract text"
            elif "corrupted" in error_str or "damaged" in error_str:
                error_msg = "PDF file appears to be corrupted or damaged"
            elif "not a pdf" in error_str:
                error_msg = "File is not a valid PDF format"
            else:
                error_msg = f"PDF parsing failed: {str(e)}"
                
            self.logger.error(error_msg)
            result["parsing_status"] = "failed" 
            result["errors"].append(error_msg)
            return result
    
    def _extract_job_number(self, text: str) -> Optional[str]:
        """
        Extract job number from PDF text
        
        Job numbers are typically 5-digit numbers that appear in various contexts.
        Common patterns: "Job 82334", "Job: 82334", "82334", etc.
        
        Args:
            text (str): Combined PDF text
            
        Returns:
            Optional[str]: Job number if found (e.g., "82334")
        """
        import re
        
        # Pattern 1: Look for "Job" followed by number
        job_pattern = re.search(r'job\s*:?\s*(\d{5})', text, re.IGNORECASE)
        if job_pattern:
            job_number = job_pattern.group(1)
            self.logger.info(f"Found job number with 'Job' keyword: {job_number}")
            return job_number
        
        # Pattern 2: Look for 5-digit numbers in context that suggests job numbers
        # Common contexts: "Job No", "Work Order", "WO", "Order", etc.
        context_pattern = re.search(r'(?:job\s*(?:no|number)|work\s*order|w\.?o\.?|order)\s*:?\s*(\d{5})', text, re.IGNORECASE)
        if context_pattern:
            job_number = context_pattern.group(1)
            self.logger.info(f"Found job number with context: {job_number}")
            return job_number
        
        # Pattern 3: Look for standalone 5-digit numbers (be more careful here)
        # Only consider numbers that appear in likely job contexts
        five_digit_matches = re.findall(r'\b(\d{5})\b', text)
        
        if five_digit_matches:
            # Filter out numbers that are likely NOT job numbers
            for number in five_digit_matches:
                # Skip numbers that start with certain prefixes that indicate other things
                if not (number.startswith('80') or number.startswith('90')):  # Board serials often start with 80
                    self.logger.info(f"Found potential job number (5-digit): {number}")
                    return number
        
        self.logger.warning("No job number found in PDF")
        return None
    
    def _extract_work_instruction(self, text: str) -> Optional[str]:
        """
        Extract work instruction from PDF text
        
        Work instructions follow the pattern "DRW-XXXX-YY" where:
        - DRW = Drawing prefix
        - XXXX = 4-digit number
        - YY = 2-digit revision/suffix
        
        Args:
            text (str): Combined PDF text
            
        Returns:
            Optional[str]: Work instruction if found (e.g., "DRW-1608-03")
        """
        import re
        
        # Pattern 1: Standard DRW-XXXX-YY format
        drw_pattern = re.search(r'DRW-\d{4}-\d{2}', text, re.IGNORECASE)
        if drw_pattern:
            work_instruction = drw_pattern.group(0).upper()
            self.logger.info(f"Found work instruction: {work_instruction}")
            return work_instruction
        
        # Pattern 2: Variations with different separators or spacing
        drw_variant_pattern = re.search(r'DRW\s*[-_]?\s*(\d{4})\s*[-_]?\s*(\d{2})', text, re.IGNORECASE)
        if drw_variant_pattern:
            work_instruction = f"DRW-{drw_variant_pattern.group(1)}-{drw_variant_pattern.group(2)}"
            self.logger.info(f"Found work instruction (variant format): {work_instruction}")
            return work_instruction
        
        # Pattern 3: Look for similar patterns with different prefixes
        # Sometimes documents use "Drawing", "Dwg", or other variants
        drawing_pattern = re.search(r'(?:drawing|dwg)\s*[-:]?\s*(\d{4})[-_]?(\d{2})', text, re.IGNORECASE)
        if drawing_pattern:
            work_instruction = f"DRW-{drawing_pattern.group(1)}-{drawing_pattern.group(2)}"
            self.logger.info(f"Found work instruction (drawing format): {work_instruction}")
            return work_instruction
        
        self.logger.warning("No work instruction found in PDF")
        return None
    
    def _find_seq_20_section(self, text: str, tables: List[Dict]) -> Dict[str, Any]:
        """
        Find and extract Seq 20 section data from PDF text and tables
        
        Args:
            text (str): Combined text from all PDF pages
            tables (List[Dict]): Extracted tables from PDF
            
        Returns:
            Dict[str, Any]: Seq 20 section data:
            {
                "found": True/False,
                "unit_serial": "1619",
                "board_serials": ["80751-0053", "80641-0022"],
                "source_table": {...},  # Table where Seq 20 was found
                "text_location": "page 2, line 15",
                "raw_data": [...],      # Raw table rows
                "extraction_method": "table" or "text"
            }
        """
        
        result = {
            "found": False,
            "unit_serial": None,
            "board_serials": [],
            "source_table": None,
            "text_location": None,
            "raw_data": [],
            "extraction_method": None
        }
        
        # Method 1: Search for Seq 20 in tables (preferred method)
        seq_20_table = self._find_seq_20_in_tables(tables)
        if seq_20_table:
            result.update(seq_20_table)
            result["extraction_method"] = "table"
            self.logger.info(f"Found Seq 20 section in table on page {seq_20_table.get('page_number', 'unknown')}")
            return result
        
        # Method 2: Search for Seq 20 in text (fallback method)
        seq_20_text = self._find_seq_20_in_text(text)
        if seq_20_text:
            result.update(seq_20_text)
            result["extraction_method"] = "text"
            self.logger.info("Found Seq 20 section in text content")
            return result
        
        # Method 3: Search for serial patterns without explicit "Seq 20" marker
        serial_patterns = self._find_serial_patterns(text, tables)
        if serial_patterns:
            result.update(serial_patterns)
            result["extraction_method"] = "pattern_matching"
            self.logger.info("Found serial patterns (fallback method)")
            return result
        
        self.logger.warning("Seq 20 section not found in PDF")
        return result
    
    def _find_seq_20_in_tables(self, tables: List[Dict]) -> Optional[Dict[str, Any]]:
        """Search for Seq 20 section in extracted tables"""
        import re
        
        for table_info in tables:
            table_data = table_info["table_data"]
            
            # Search for "Seq 20" or similar patterns in table cells
            for row_idx, row in enumerate(table_data):
                for col_idx, cell in enumerate(row or []):
                    if cell and isinstance(cell, str):
                        # Look for Seq 20 pattern (case insensitive)
                        if re.search(r'seq\s*20', cell.lower()):
                            # Found Seq 20 reference, extract serials from surrounding rows
                            serials = self._extract_serials_from_table_section(table_data, row_idx)
                            
                            return {
                                "found": True,
                                "unit_serial": serials.get("unit_serial"),
                                "board_serials": serials.get("board_serials", []),
                                "source_table": table_info,
                                "page_number": table_info["page_number"],
                                "raw_data": table_data[max(0, row_idx-2):row_idx+5]  # Context rows
                            }
        
        return None
    
    def _find_seq_20_in_text(self, text: str) -> Optional[Dict[str, Any]]:
        """Search for Seq 20 section in text content"""
        import re
        
        # Look for Seq 20 pattern in text
        seq_20_match = re.search(r'seq\s*20.*?(?=seq\s*\d+|$)', text.lower(), re.DOTALL | re.IGNORECASE)
        
        if seq_20_match:
            seq_20_text = seq_20_match.group(0)
            
            # Extract serials from the Seq 20 text section
            unit_serial = self._extract_unit_serial_from_text(seq_20_text)
            board_serials = self._extract_board_serials_from_text(seq_20_text)
            
            return {
                "found": True,
                "unit_serial": unit_serial,
                "board_serials": board_serials,
                "text_location": f"Character position {seq_20_match.start()}-{seq_20_match.end()}",
                "raw_data": seq_20_text
            }
        
        return None
    
    def _find_serial_patterns(self, text: str, tables: List[Dict]) -> Optional[Dict[str, Any]]:
        """Fallback: Look for serial number patterns without explicit Seq 20 marker"""
        import re
        
        # Look for patterns like "INF-1619" (unit serial) and "VGN-80751-0053" (board serial)
        unit_serial_matches = re.findall(r'INF-?\d{4}', text, re.IGNORECASE)
        board_serial_matches = re.findall(r'VGN-?\d{5}-?\d{4}', text, re.IGNORECASE)
        
        # Also look for raw numbers that could be serials (4 digits for unit, 5-4 pattern for boards)
        raw_unit_matches = re.findall(r'\b\d{4}\b', text)
        raw_board_matches = re.findall(r'\b\d{5}-\d{4}\b', text)
        
        if unit_serial_matches or board_serial_matches or raw_unit_matches or raw_board_matches:
            return {
                "found": True,
                "unit_serial": unit_serial_matches[0] if unit_serial_matches else (raw_unit_matches[0] if raw_unit_matches else None),
                "board_serials": board_serial_matches + raw_board_matches,
                "raw_data": {
                    "unit_matches": unit_serial_matches,
                    "board_matches": board_serial_matches,
                    "raw_unit_matches": raw_unit_matches,
                    "raw_board_matches": raw_board_matches
                }
            }
        
        return None
    
    def _extract_serials_from_table_section(self, table_data: List[List], seq_row_idx: int) -> Dict[str, Any]:
        """Extract serial numbers from table rows around Seq 20 reference"""
        import re
        
        serials = {
            "unit_serial": None,
            "board_serials": []
        }
        
        # Look in rows around the Seq 20 reference (before and after)
        start_row = max(0, seq_row_idx - 2)
        end_row = min(len(table_data), seq_row_idx + 5)
        
        for row_idx in range(start_row, end_row):
            if row_idx < len(table_data) and table_data[row_idx]:
                for cell in table_data[row_idx]:
                    if cell and isinstance(cell, str):
                        # Look for unit serial patterns (4 digits, possibly with INF prefix)
                        unit_match = re.search(r'(INF-?)?\d{4}', cell, re.IGNORECASE)
                        if unit_match and not serials["unit_serial"]:
                            serials["unit_serial"] = unit_match.group(0)
                        
                        # Look for board serial patterns (5-4 digit pattern, possibly with VGN prefix)
                        board_matches = re.findall(r'(VGN-?)?\d{5}-?\d{4}', cell, re.IGNORECASE)
                        for match in board_matches:
                            if match not in serials["board_serials"]:
                                serials["board_serials"].append(match)
        
        return serials
    
    def _extract_unit_serial_from_text(self, text: str) -> Optional[str]:
        """Extract unit serial from text section"""
        import re
        
        # Look for INF-#### pattern first, then raw 4-digit numbers
        unit_match = re.search(r'INF-?\d{4}', text, re.IGNORECASE)
        if unit_match:
            return unit_match.group(0)
        
        # Fallback to 4-digit numbers
        raw_match = re.search(r'\b\d{4}\b', text)
        if raw_match:
            return raw_match.group(0)
        
        return None
    
    def _extract_board_serials_from_text(self, text: str) -> List[str]:
        """Extract board serials from text section"""
        import re
        
        board_serials = []
        
        # Look for VGN-#####-#### pattern
        vgn_matches = re.findall(r'VGN-?\d{5}-?\d{4}', text, re.IGNORECASE)
        board_serials.extend(vgn_matches)
        
        # Look for raw #####-#### pattern
        raw_matches = re.findall(r'\b\d{5}-\d{4}\b', text)
        board_serials.extend(raw_matches)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_serials = []
        for serial in board_serials:
            if serial.lower() not in seen:
                seen.add(serial.lower())
                unique_serials.append(serial)
        
        return unique_serials
    
    def _extract_part_numbers(self, text: str) -> List[Dict[str, str]]:
        """
        Extract part numbers with revisions from PDF text
        
        Part numbers typically follow patterns like:
        - PCA-1153-03 Rev F
        - PCA-1052-05 Rev B
        - HOUSING-001 Rev C
        
        Args:
            text (str): Combined PDF text
            
        Returns:
            List[Dict[str, str]]: List of part number dictionaries:
            [
                {"part": "PCA-1153-03", "revision": "F", "full_text": "PCA-1153-03 Rev F"},
                {"part": "PCA-1052-05", "revision": "B", "full_text": "PCA-1052-05 Rev B"}
            ]
        """
        import re
        
        part_numbers = []
        
        # Pattern 1: PCA-XXXX-YY Rev Z format
        pca_pattern = re.finditer(r'(PCA-\d{4}-\d{2})\s*(?:Rev\s*([A-Z]\d*))?', text, re.IGNORECASE)
        
        for match in pca_pattern:
            part_num = match.group(1).upper()
            revision = match.group(2).upper() if match.group(2) else None
            full_text = match.group(0)
            
            part_numbers.append({
                "part": part_num,
                "revision": revision,
                "full_text": full_text.strip()
            })
        
        # Pattern 2: Other part number formats (HOUSING, etc.)
        other_pattern = re.finditer(r'([A-Z]+(?:-\d+)+)\s*(?:Rev\s*([A-Z]\d*))?', text, re.IGNORECASE)
        
        for match in other_pattern:
            part_num = match.group(1).upper()
            revision = match.group(2).upper() if match.group(2) else None
            full_text = match.group(0)
            
            # Skip if already found by PCA pattern
            if not any(p["part"] == part_num for p in part_numbers):
                part_numbers.append({
                    "part": part_num,
                    "revision": revision,
                    "full_text": full_text.strip()
                })
        
        # Remove duplicates while preserving order
        seen = set()
        unique_parts = []
        
        for part in part_numbers:
            key = (part["part"], part["revision"])
            if key not in seen:
                seen.add(key)
                unique_parts.append(part)
        
        if unique_parts:
            part_list = [f"{p['part']}{' Rev ' + p['revision'] if p['revision'] else ''}" for p in unique_parts]
            self.logger.info(f"Found {len(unique_parts)} part numbers: {', '.join(part_list)}")
        else:
            self.logger.warning("No part numbers found in PDF")
        
        return unique_parts
    
    def get_text_summary(self, parsing_result: Dict[str, Any]) -> str:
        """
        Get a summary of extracted text for debugging and logging
        
        Args:
            parsing_result: Result from parse_traveler_pdf()
            
        Returns:
            str: Human-readable summary of extracted text
        """
        if parsing_result["parsing_status"] != "success":
            return f"Parsing failed: {', '.join(parsing_result['errors'])}"
        
        page_count = len(parsing_result["page_texts"])
        total_chars = sum(page.get("char_count", 0) for page in parsing_result["page_texts"])
        
        summary = f"PDF Summary: {page_count} pages, {total_chars} total characters"
        
        if parsing_result["pdf_info"]:
            pdf_info = parsing_result["pdf_info"]
            if "total_pages" in pdf_info:
                summary += f", {pdf_info['total_pages']} PDF pages"
        
        # Add preview of first 200 characters
        if parsing_result["raw_text"]:
            preview = parsing_result["raw_text"][:200].replace('\n', ' ').strip()
            summary += f"\nText preview: {preview}..."
        
        return summary
    
    def _validate_extracted_data(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate extracted data formats and quality
        
        Args:
            result: Parsing result dictionary
            
        Returns:
            Dict[str, Any]: Validation results:
            {
                "is_valid": True/False,
                "job_number_valid": True/False,
                "work_instruction_valid": True/False,
                "unit_serial_valid": True/False,
                "board_serials_valid": True/False,
                "completeness_score": 0.8,  # 0-1 scale
                "validation_errors": [],
                "validation_warnings": []
            }
        """
        import re
        
        validation = {
            "is_valid": True,
            "job_number_valid": False,
            "work_instruction_valid": False,
            "unit_serial_valid": False,
            "board_serials_valid": False,
            "completeness_score": 0.0,
            "validation_errors": [],
            "validation_warnings": []
        }
        
        # Validate job number format (5 digits)
        if result["job_number"]:
            if re.match(r'^\d{5}$', result["job_number"]):
                validation["job_number_valid"] = True
            else:
                validation["validation_errors"].append(f"Job number format invalid: '{result['job_number']}' (expected 5 digits)")
                validation["is_valid"] = False
        
        # Validate work instruction format (DRW-XXXX-YY)
        if result["work_instruction"]:
            if re.match(r'^DRW-\d{4}-\d{2}$', result["work_instruction"], re.IGNORECASE):
                validation["work_instruction_valid"] = True
            else:
                validation["validation_errors"].append(f"Work instruction format invalid: '{result['work_instruction']}' (expected DRW-XXXX-YY)")
                validation["is_valid"] = False
        
        # Validate unit serial format
        if result["unit_serial"]:
            # Accept both INF-XXXX and raw XXXX formats
            if re.match(r'^(INF-?)?\d{4}$', result["unit_serial"], re.IGNORECASE):
                validation["unit_serial_valid"] = True
                
                # Warn if missing INF prefix
                if not result["unit_serial"].upper().startswith("INF"):
                    validation["validation_warnings"].append(f"Unit serial missing INF- prefix: '{result['unit_serial']}'")
            else:
                validation["validation_errors"].append(f"Unit serial format invalid: '{result['unit_serial']}' (expected INF-XXXX or XXXX)")
                validation["is_valid"] = False
        
        # Validate board serials format
        if result["board_serials"]:
            valid_board_serials = 0
            for serial in result["board_serials"]:
                # Accept both VGN-XXXXX-XXXX and raw XXXXX-XXXX formats
                if re.match(r'^(VGN-?)?\d{5}-?\d{4}$', serial, re.IGNORECASE):
                    valid_board_serials += 1
                    
                    # Warn if missing VGN prefix
                    if not serial.upper().startswith("VGN"):
                        validation["validation_warnings"].append(f"Board serial missing VGN- prefix: '{serial}'")
                else:
                    validation["validation_errors"].append(f"Board serial format invalid: '{serial}' (expected VGN-XXXXX-XXXX or XXXXX-XXXX)")
                    validation["is_valid"] = False
            
            validation["board_serials_valid"] = valid_board_serials == len(result["board_serials"])
        
        # Validate part numbers format  
        part_number_issues = 0
        for part in result["part_numbers"]:
            part_num = part.get("part", "")
            
            # Check common part number patterns
            if not re.match(r'^[A-Z]+-\d+(-\d+)*$', part_num):
                validation["validation_warnings"].append(f"Part number format unusual: '{part_num}'")
                part_number_issues += 1
        
        # Calculate completeness score (0-1 normalized)
        completeness_factors = [
            1.0 if result["job_number"] else 0.0,                    # Job number (critical)
            1.0 if result["work_instruction"] else 0.0,             # Work instruction (critical)
            0.5 if result["unit_serial"] else 0.0,                  # Unit serial (moderate)
            0.5 if result["board_serials"] else 0.0,                # Board serials (moderate)
            0.3 if result["part_numbers"] else 0.0,                 # Part numbers (nice to have)
            0.2 if result["seq_20_data"].get("found") else 0.0,     # Seq 20 found (structural)
            0.1 if result["tables"] else 0.0,                       # Tables extracted (structural)
            0.1 if len(result["page_texts"]) > 0 else 0.0           # Text extracted (basic)
        ]
        
        # Normalize to 0-1 scale (max possible sum is 3.7)
        MAX_POSSIBLE_SCORE = 3.7
        raw_score = sum(completeness_factors)
        validation["completeness_score"] = raw_score / MAX_POSSIBLE_SCORE
        
        # Overall validity check
        if validation["completeness_score"] < 0.3:
            validation["validation_errors"].append("PDF appears to have very limited extractable data")
            validation["is_valid"] = False
        
        # Summary logging
        if validation["is_valid"]:
            self.logger.info(f"Data validation passed (completeness: {validation['completeness_score']:.1%})")
        else:
            error_count = len(validation["validation_errors"])
            self.logger.warning(f"Data validation failed with {error_count} errors")
        
        return validation

# Create singleton instance for service
pdf_parser_service = TravelerPDFParser()
