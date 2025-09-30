# app/utils/file_handlers.py
import os
import shutil
from pathlib import Path
from fastapi import UploadFile
from ..models.file import FileType
from ..config import settings

def validate_file_type(filename: str, file_type: FileType) -> bool:
    """
    Validate that file extension matches the declared file type
    """
    extension = Path(filename).suffix.lower()
    allowed_extensions = settings.ALLOWED_EXTENSIONS.get(file_type.value, [])
    return extension in allowed_extensions

def save_upload_file(upload_file: UploadFile, session_id: str, file_type: FileType) -> str:
    """
    Save uploaded file to disk
    Returns storage path
    
    File structure:
    uploads/
      {session_id}/
        traveler/
          {filename}
        image/
          {filename}
        bom/
          {filename}
    """
    # Create session directory
    session_dir = os.path.join(settings.UPLOAD_DIR, session_id, file_type.value)
    os.makedirs(session_dir, exist_ok=True)
    
    # Generate storage path
    storage_path = os.path.join(session_dir, upload_file.filename)
    
    # Save file
    with open(storage_path, "wb") as f:
        shutil.copyfileobj(upload_file.file, f)
    
    return storage_path

def delete_session_files(session_id: str):
    """
    Delete all uploaded files for a session
    """
    session_dir = os.path.join(settings.UPLOAD_DIR, session_id)
    if os.path.exists(session_dir):
        shutil.rmtree(session_dir)
