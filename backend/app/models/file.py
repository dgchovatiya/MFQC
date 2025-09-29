# app/models/file.py
from sqlalchemy import Column, String, Integer, DateTime, Enum as SQLEnum, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum
from ..database import Base

class FileType(str, enum.Enum):
    """Type of uploaded file"""
    TRAVELER = "traveler"
    IMAGE = "image"
    BOM = "bom"

class ProcessingStatus(str, enum.Enum):
    """File processing status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class UploadedFile(Base):
    """
    Represents an uploaded file
    Stores metadata and extracted data
    """
    __tablename__ = "uploaded_files"
    
    # Primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Foreign key to session
    session_id = Column(String(36), ForeignKey("sessions.id"), nullable=False)
    
    # File metadata
    filename = Column(String(255), nullable=False)
    file_type = Column(SQLEnum(FileType), nullable=False)
    storage_path = Column(String(500), nullable=False)  # Path on disk
    file_size = Column(Integer, nullable=False)  # Bytes
    
    # Processing
    processing_status = Column(SQLEnum(ProcessingStatus), default=ProcessingStatus.PENDING)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)
    
    # Extracted data (JSON field)
    extracted_data = Column(JSON, nullable=True)
    # Example structure:
    # {
    #   "job_number": "82334",
    #   "unit_serial": "1619",
    #   "board_serials": ["80751-0053", ...],
    #   "part_numbers": ["PCA-1153-03", ...]
    # }
    
    # Relationships
    session = relationship("Session", back_populates="files")
    
    def __repr__(self):
        return f"<UploadedFile {self.filename} type={self.file_type}>"
