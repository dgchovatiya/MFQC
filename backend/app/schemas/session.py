# app/schemas/session.py
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from ..models.session import SessionStatus, OverallResult

# Request schemas
class SessionCreate(BaseModel):
    """Schema for creating a new session"""
    # No fields required - session is created empty
    pass

# Response schemas
class SessionResponse(BaseModel):
    """Schema for session response"""
    id: str
    created_at: datetime
    updated_at: datetime
    status: SessionStatus
    overall_result: Optional[OverallResult] = None
    
    class Config:
        from_attributes = True  # Pydantic v2

class SessionListResponse(BaseModel):
    """Schema for list of sessions"""
    sessions: List[SessionResponse]
    total: int
