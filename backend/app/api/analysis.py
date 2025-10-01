# app/api/analysis.py
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.session import Session as SessionModel, SessionStatus
from ..models.file import UploadedFile, FileType, ProcessingStatus
from ..schemas.session import SessionResponse
from ..services.pdf_parser import pdf_parser_service
from ..logging_config import get_logger
from datetime import datetime

logger = get_logger(__name__)

router = APIRouter()

@router.post("/{session_id}/analyze", response_model=SessionResponse, status_code=202)
def start_analysis(
    session_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Trigger analysis pipeline for a session
    Returns 202 Accepted (processing in background)
    """
    # Get session
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    
    # Check session status
    if session.status == SessionStatus.PROCESSING:
        raise HTTPException(status_code=409, detail="Analysis already in progress")
    
    if session.status == SessionStatus.COMPLETED:
        raise HTTPException(status_code=409, detail="Session already analyzed")
    
    # Check required files are uploaded with correct counts
    files = db.query(UploadedFile).filter(UploadedFile.session_id == session_id).all()
    
    # Count files by type
    traveler_count = len([f for f in files if f.file_type == FileType.TRAVELER])
    image_count = len([f for f in files if f.file_type == FileType.IMAGE])
    bom_count = len([f for f in files if f.file_type == FileType.BOM])
    
    # Validate file counts precisely
    if traveler_count != 1:
        if traveler_count == 0:
            raise HTTPException(status_code=400, detail="Exactly 1 Traveler PDF required, found 0")
        else:
            raise HTTPException(
                status_code=400, 
                detail=f"Exactly 1 Traveler PDF required, found {traveler_count}. Please delete duplicates."
            )
    
    if image_count != 1:
        if image_count == 0:
            raise HTTPException(status_code=400, detail="Exactly 1 Product Image required, found 0")
        else:
            raise HTTPException(
                status_code=400, 
                detail=f"Exactly 1 Product Image required, found {image_count}. Please delete duplicates."
            )
    
    if bom_count < 1 or bom_count > 4:
        if bom_count == 0:
            raise HTTPException(status_code=400, detail="At least 1 BOM Excel file required, found 0")
        else:
            raise HTTPException(
                status_code=400,
                detail=f"1-4 BOM Excel files required, found {bom_count}. Please remove excess BOM files."
            )
    
    # Files are processed during analysis, not during upload
    # All validation of file contents happens in the background pipeline
    
    # Update session status
    session.status = SessionStatus.PROCESSING
    db.commit()
    
    # Add background task for validation pipeline
    background_tasks.add_task(run_validation_pipeline, session_id, db)
    
    return session


def run_validation_pipeline(session_id: str, db: Session):
    """
    Background task to run the complete validation pipeline
    
    Processes all uploaded files in coordinated sequence:
    1. Parse PDF Traveler documents
    2. Run OCR on product images (Phase 6) 
    3. Parse Excel BOM files (Phase 7)
    4. Normalize data (Phase 8)
    5. Run 7 validation checks (Phase 9)
    """
    
    try:
        logger.info(f"Starting validation pipeline for session {session_id}")
        
        # Get session and files
        session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        if not session:
            logger.error(f"Session {session_id} not found in pipeline")
            return
        
        files = db.query(UploadedFile).filter(UploadedFile.session_id == session_id).all()
        
        # Organize files by type
        traveler_file = next((f for f in files if f.file_type == FileType.TRAVELER), None)
        image_files = [f for f in files if f.file_type == FileType.IMAGE]
        bom_files = [f for f in files if f.file_type == FileType.BOM]
        
        # =============================================================================
        # PHASE 5: PROCESS PDF TRAVELER DOCUMENTS  
        # =============================================================================
        traveler_data = {}
        if traveler_file:
            logger.info(f"Processing Traveler PDF: {traveler_file.filename}")
            
            try:
                # Update file processing status
                traveler_file.processing_status = ProcessingStatus.PROCESSING
                db.commit()
                
                # Parse PDF using PDF parser service
                parsing_result = pdf_parser_service.parse_traveler_pdf(traveler_file.storage_path)
                
                # Store extracted data in database
                traveler_file.extracted_data = parsing_result
                traveler_data = parsing_result
                
                # Update processing status based on result
                if parsing_result.get("parsing_status") == "success":
                    traveler_file.processing_status = ProcessingStatus.COMPLETED
                    logger.info(f"Successfully processed {traveler_file.filename}")
                    
                    # Log extracted manufacturing data
                    validation = traveler_data.get('validation', {})
                    score = validation.get('completeness_score', 0) * 100  # Convert to percentage
                    
                    logger.info(f"Extracted Data Summary:")
                    logger.info(f"  - Job Number: {traveler_data.get('job_number', 'N/A')}")
                    logger.info(f"  - Work Instruction: {traveler_data.get('work_instruction', 'N/A')}")
                    logger.info(f"  - Unit Serial: {traveler_data.get('unit_serial', 'N/A')}")
                    logger.info(f"  - Board Serials: {len(traveler_data.get('board_serials', []))} found")
                    logger.info(f"  - Part Numbers: {len(traveler_data.get('part_numbers', []))} found")
                    logger.info(f"  - Seq 20 Found: {traveler_data.get('seq_20_data', {}).get('found', False)}")
                    logger.info(f"  - Completeness Score: {score:.1f}%")
                    
                    # Log warnings if any
                    warnings = validation.get('validation_warnings', [])
                    if warnings:
                        logger.warning(f"Data validation warnings: {len(warnings)} issues")
                        for warning in warnings:
                            logger.warning(f"  - {warning}")
                else:
                    traveler_file.processing_status = ProcessingStatus.FAILED
                    logger.error(f"Failed to process {traveler_file.filename}")
                    errors = parsing_result.get('errors', [])
                    for error in errors:
                        logger.error(f"  - {error}")
                
                db.commit()
                
            except Exception as e:
                error_msg = f"PDF processing failed: {str(e)}"
                traveler_file.processing_status = ProcessingStatus.FAILED
                traveler_file.extracted_data = {
                    "parsing_status": "failed", 
                    "errors": [error_msg]
                }
                db.commit()
                logger.exception(f"Exception processing {traveler_file.filename}: {e}")
        
        # =============================================================================
        # PHASE 6: PROCESS PRODUCT IMAGES (OCR) - PLACEHOLDER
        # =============================================================================
        image_data = []
        for image_file in image_files:
            logger.info(f"Phase 6: OCR processing for {image_file.filename} - TODO")
            # TODO: Implement OCR processing in Phase 6
            image_file.processing_status = ProcessingStatus.PENDING  # Will be COMPLETED in Phase 6
            # TODO: Extract board serials, part numbers, flight status from images
        
        # =============================================================================
        # PHASE 7: PROCESS EXCEL BOM FILES - PLACEHOLDER  
        # =============================================================================
        bom_data = []
        for bom_file in bom_files:
            logger.info(f"Phase 7: Excel BOM parsing for {bom_file.filename} - TODO")
            # TODO: Implement Excel parsing in Phase 7
            bom_file.processing_status = ProcessingStatus.PENDING  # Will be COMPLETED in Phase 7
            # TODO: Extract job numbers, part numbers, revisions from Excel
        
        # =============================================================================
        # PHASE 8: DATA NORMALIZATION - PLACEHOLDER
        # =============================================================================
        logger.info("Phase 8: Data normalization (VGN-, INF- prefixes) - TODO")
        
        # =============================================================================
        # PHASE 9: VALIDATION CHECKS - PLACEHOLDER
        # =============================================================================
        logger.info("Phase 9: 7-check validation engine - TODO")
        
        # =============================================================================
        # COMPLETE PIPELINE
        # =============================================================================
        session.status = SessionStatus.COMPLETED
        session.overall_result = None  # Will be set by validation engine in Phase 9
        session.updated_at = datetime.utcnow()
        
        db.commit()
        
        logger.info(f"Validation pipeline completed successfully for session {session_id}")
        
    except Exception as e:
        # Handle pipeline errors
        logger.exception(f"Pipeline failed for session {session_id}: {str(e)}")
        
        try:
            if session:
                session.status = SessionStatus.FAILED
                session.updated_at = datetime.utcnow()
                db.commit()
        except Exception as db_error:
            logger.error(f"Failed to update session status: {db_error}")

@router.get("/{session_id}/status", response_model=SessionResponse)
def get_analysis_status(
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    Check analysis progress
    Returns session status and overall result
    """
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    
    return session
