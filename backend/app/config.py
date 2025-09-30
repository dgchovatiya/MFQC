# app/config.py
from pydantic_settings import BaseSettings
from typing import List, Optional

class Settings(BaseSettings):
    """Application configuration using Pydantic settings"""
    
    # App Info
    APP_NAME: str = "Manufacturing QC System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # Database
    DATABASE_URL: str = "sqlite:///./qc_system.db"
    
    # File Upload
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE: int = 50 * 1024 * 1024  # 10 MB
    ALLOWED_EXTENSIONS: dict = {
        "traveler": [".pdf"],
        "image": [".jpg", ".jpeg", ".png"],
        "bom": [".xlsx", ".xlsm"]
    }
    
    # CORS
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",  # Vite default
    ]
    
    # OCR Settings
    TESSERACT_CMD: Optional[str] = None  # Auto-detect, or set path if needed
    OCR_LANGUAGE: str = "eng"
    
    # Validation Settings
    ENABLE_STRICT_VALIDATION: bool = False  # If True, treat warnings as fails
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Singleton instance
settings = Settings()
