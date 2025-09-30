# app/api/results.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.session import Session as SessionModel
from ..models.result import ValidationResult
from ..schemas.result import ResultListResponse

router = APIRouter()

@router.get("/{session_id}/results", response_model=ResultListResponse)
def get_results(
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    Get all validation results for a session
    """
    # Check session exists
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    
    # Get results ordered by priority
    results = db.query(ValidationResult).filter(
        ValidationResult.session_id == session_id
    ).order_by(ValidationResult.check_priority).all()
    
    return ResultListResponse(
        results=results,
        overall_status=session.overall_result.value if session.overall_result else None
    )
