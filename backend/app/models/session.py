# app/models/session.py
from sqlalchemy import Column, String, DateTime, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum
from ..database import Base

class SessionStatus(str, enum.Enum):
    """Session processing status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class OverallResult(str, enum.Enum):
    """Overall validation result"""
    PASS = "pass"
    WARNING = "warning"
    FAIL = "fail"

class Session(Base):
    """
    Represents an analysis session
    One session = one set of uploaded files + validation results
    """
    __tablename__ = "sessions"
    
    # Primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Status tracking
    status = Column(SQLEnum(SessionStatus), default=SessionStatus.PENDING, nullable=False)
    overall_result = Column(SQLEnum(OverallResult), nullable=True)
    
    # Relationships
    files = relationship("UploadedFile", back_populates="session", cascade="all, delete-orphan")
    results = relationship("ValidationResult", back_populates="session", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Session {self.id} status={self.status} result={self.overall_result}>"
