# app/schemas/file.py
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict, Any
from ..models.file import FileType, ProcessingStatus

# Response schemas
class FileResponse(BaseModel):
    """Schema for file response"""
    id: str
    session_id: str
    filename: str
    file_type: FileType
    file_size: int
    processing_status: ProcessingStatus
    uploaded_at: datetime
    processed_at: Optional[datetime] = None
    extracted_data: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True
