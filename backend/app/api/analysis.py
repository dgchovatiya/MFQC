# app/api/analysis.py
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.session import Session as SessionModel, SessionStatus
from ..models.file import UploadedFile, FileType
from ..schemas.session import SessionResponse

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
    
    # Update session status
    session.status = SessionStatus.PROCESSING
    db.commit()
    
    # Add background task (will implement pipeline in Phases 5-9)
    # background_tasks.add_task(run_validation_pipeline, session_id)
    
    # For now, just return the updated session
    return session

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
