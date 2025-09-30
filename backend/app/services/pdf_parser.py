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
                
                # Extract text from all pages
                all_text = ""
                page_texts = []
                
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
                            
                    except Exception as page_error:
                        error_msg = f"Error extracting text from page {page_num}: {str(page_error)}"
                        self.logger.warning(error_msg)
                        result["errors"].append(error_msg)
                
                # Store extracted text data
                result["raw_text"] = all_text.strip()
                result["page_texts"] = page_texts
                result["pdf_info"] = pdf_info
                
                # Basic validation of extracted content
                if not all_text.strip():
                    raise Exception("No text could be extracted from PDF - file may be image-based or corrupted")
                
                if len(page_texts) == 0:
                    raise Exception("No readable pages found in PDF")
                
                # Log extraction statistics
                total_chars = sum(page["char_count"] for page in page_texts)
                self.logger.info(f"PDF text extraction completed: {len(page_texts)} pages, {total_chars} characters")
                
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
        """Extract job number from PDF text (placeholder for substep 4)"""
        # TODO: Implement job number extraction logic
        return None
    
    def _extract_work_instruction(self, text: str) -> Optional[str]:
        """Extract work instruction from PDF text (placeholder for substep 4)"""  
        # TODO: Implement work instruction extraction logic
        return None
    
    def _find_seq_20_section(self, pages: List) -> Dict[str, Any]:
        """Find and extract Seq 20 section data (placeholder for substep 3)"""
        # TODO: Implement Seq 20 section detection logic
        return {}
    
    def _extract_part_numbers(self, text: str) -> List[Dict[str, str]]:
        """Extract part numbers with revisions (placeholder for substep 3)"""
        # TODO: Implement part number extraction logic  
        return []
    
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

# Create singleton instance for service
pdf_parser_service = TravelerPDFParser()
