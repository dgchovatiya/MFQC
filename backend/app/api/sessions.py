# app/api/sessions.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..models.session import Session as SessionModel, SessionStatus
from ..schemas.session import SessionCreate, SessionResponse, SessionListResponse
from datetime import datetime

router = APIRouter()

@router.post("/", 
             response_model=SessionResponse, 
             status_code=201,
             summary="Create New Analysis Session",
             description="""
             Create a new analysis session for manufacturing QC validation.
             
             This endpoint initializes a new session that will be used to:
             - Upload manufacturing documents (Traveler PDF, Product Images, BOM Excel files)
             - Trigger validation pipeline
             - Store analysis results and evidence
             
             **Returns**: Session ID required for all subsequent operations
             """,
             response_description="Session created successfully with unique ID")
def create_session(
    session_data: SessionCreate,
    db: Session = Depends(get_db)
):
    """Create a new analysis session"""
    # Create new session
    new_session = SessionModel(
        status=SessionStatus.PENDING,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    
    return new_session

@router.get("/", response_model=SessionListResponse)
def list_sessions(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: str = Query(None),
    db: Session = Depends(get_db)
):
    """
    List all sessions with pagination
    Optional filter by status
    """
    query = db.query(SessionModel)
    
    # Filter by status if provided
    if status:
        try:
            status_enum = SessionStatus(status)
            query = query.filter(SessionModel.status == status_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    
    # Get total count
    total = query.count()
    
    # Apply pagination and order by newest first
    sessions = query.order_by(SessionModel.created_at.desc()).offset(skip).limit(limit).all()
    
    return SessionListResponse(sessions=sessions, total=total)

@router.get("/{session_id}", response_model=SessionResponse)
def get_session(
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    Get a specific session by ID
    Includes files and results
    """
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    
    return session

@router.delete("/{session_id}", status_code=204)
def delete_session(
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    Delete a session and all associated files/results
    """
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    
    # Delete from database (cascades to files and results)
    db.delete(session)
    db.commit()
    
    # TODO: Also delete uploaded files from disk (Phase 3.3)
    
    return None
