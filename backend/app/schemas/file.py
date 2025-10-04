# app/schemas/file.py
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict, Any
from ..models.file import FileType, ProcessingStatus

# Response schemas
class FileBasicResponse(BaseModel):
    """
    Lightweight schema for file tracking without extracted data.
    Use this for listing files when extracted data is not needed.
    """
    id: str
    session_id: str
    filename: str
    file_type: FileType
    file_size: int
    processing_status: ProcessingStatus
    uploaded_at: datetime
    processed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class FileResponse(BaseModel):
    """
    Complete schema for file response including extracted data.
    Use this when full file details with extraction results are needed.
    """
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
