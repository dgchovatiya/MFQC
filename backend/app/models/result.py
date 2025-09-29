# app/models/result.py
from sqlalchemy import Column, String, Integer, Text, DateTime, Enum as SQLEnum, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum
from ..database import Base

class CheckStatus(str, enum.Enum):
    """Validation check status"""
    PASS = "pass"
    WARNING = "warning"
    FAIL = "fail"
    INFO = "info"

class ValidationResult(Base):
    """
    Represents a single validation check result
    Each session has multiple validation results (7 checks)
    """
    __tablename__ = "validation_results"
    
    # Primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Foreign key to session
    session_id = Column(String(36), ForeignKey("sessions.id"), nullable=False)
    
    # Check info
    check_name = Column(String(100), nullable=False)  # e.g., "Job Number Match"
    check_priority = Column(Integer, nullable=False)  # 1-7 (order of checks)
    
    # Result
    status = Column(SQLEnum(CheckStatus), nullable=False)
    message = Column(Text, nullable=False)  # Human-readable result
    
    # Evidence (JSON field)
    evidence = Column(JSON, nullable=True)
    # Example structure:
    # {
    #   "expected": "82334",
    #   "found": ["82334", "80751", "80641"],
    #   "source": "BOM files",
    #   "match": true
    # }
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    session = relationship("Session", back_populates="results")
    
    def __repr__(self):
        return f"<ValidationResult {self.check_name} status={self.status}>"
