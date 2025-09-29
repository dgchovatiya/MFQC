# app/schemas/result.py
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict, Any, List
from ..models.result import CheckStatus

# Response schemas
class ResultResponse(BaseModel):
    """Schema for validation result response"""
    id: str
    check_name: str
    check_priority: int
    status: CheckStatus
    message: str
    evidence: Optional[Dict[str, Any]] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class ResultListResponse(BaseModel):
    """Schema for list of validation results"""
    results: List[ResultResponse]
    overall_status: Optional[str] = None
