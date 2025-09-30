# app/api/files.py
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List
import os
import shutil
from ..database import get_db
from ..models.session import Session as SessionModel, SessionStatus
from ..models.file import UploadedFile, FileType, ProcessingStatus
from ..schemas.file import FileResponse
from ..config import settings
from ..utils.file_handlers import validate_file_type, save_upload_file

router = APIRouter()

@router.post("/{session_id}/files", 
             response_model=FileResponse, 
             status_code=201,
             summary="Upload Manufacturing Document",
             description="""
             Upload a manufacturing document to an analysis session.
             
             **File Types Supported & Limits**:
             - **traveler**: Traveler/Work Instruction PDFs (.pdf) - **Maximum 1 per session**
             - **image**: Product hardware photos (.jpg, .jpeg, .png) - **Maximum 1 per session**
             - **bom**: Bill of Materials Excel files (.xlsx, .xlsm) - **Maximum 4 per session**
             
             **File Size Limit**: 10 MB per file
             
             **Validation Rules**:
             - File extension must match declared file_type
             - File size must be within limits
             - Session must exist and be in valid state
             - Upload limits enforced (duplicate uploads rejected)
             
             **Error Handling**: 
             - 400 if attempting to upload duplicate traveler/image
             - 400 if attempting to upload 5th BOM file
             - Clear error messages with existing file names
             
             **Storage**: Files are organized by session and type for processing pipeline
             """,
             responses={
                 201: {
                     "description": "File uploaded successfully",
                     "content": {
                         "application/json": {
                             "example": {
                                 "id": "456e7890-e89b-12d3-a456-426614174001",
                                 "session_id": "123e4567-e89b-12d3-a456-426614174000",
                                 "filename": "traveler.pdf",
                                 "file_type": "traveler",
                                 "file_size": 2048576,
                                 "processing_status": "pending",
                                 "uploaded_at": "2025-09-29T16:31:00.000Z",
                                 "processed_at": None,
                                 "extracted_data": None
                             }
                         }
                     }
                 },
                 400: {
                     "description": "Validation error",
                     "content": {
                         "application/json": {
                             "examples": {
                                 "duplicate_traveler": {
                                     "summary": "Duplicate traveler upload",
                                     "value": {
                                         "detail": "Only 1 traveler file allowed per session. Existing file: 'DRW-1608-03_Traveler.pdf'. Please delete the existing file first or use a different session."
                                     }
                                 },
                                 "duplicate_image": {
                                     "summary": "Duplicate image upload", 
                                     "value": {
                                         "detail": "Only 1 image file allowed per session. Existing file: 'Hardware_Photo_INF1619.jpg'. Please delete the existing file first or use a different session."
                                     }
                                 },
                                 "too_many_boms": {
                                     "summary": "Too many BOM files",
                                     "value": {
                                         "detail": "Maximum 4 BOM files allowed per session. Found 4 existing files: ['As_Built_82334.xlsx', 'As_Built_80751.xlsm', 'As_Built_80641.xlsx', 'As_Built_82999.xlsx']. Please delete an existing BOM file first."
                                     }
                                 },
                                 "invalid_extension": {
                                     "summary": "Invalid file extension",
                                     "value": {
                                         "detail": "Invalid file type for traveler. Allowed: ['.pdf']"
                                     }
                                 }
                             }
                         }
                     }
                 },
                 404: {"description": "Session not found"},
                 413: {"description": "File size exceeds limit"}
             })
async def upload_file(
    session_id: str,
    file: UploadFile = File(..., description="Manufacturing document file"),
    file_type: str = Form(..., description="File type: 'traveler', 'image', or 'bom'"),
    db: Session = Depends(get_db)
):
    """Upload a file to a session"""
    # Check session exists
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    
    # Validate file type enum
    try:
        file_type_enum = FileType(file_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid file_type: {file_type}")
    
    # Check existing files of this type to enforce limits
    existing_files = db.query(UploadedFile).filter(
        UploadedFile.session_id == session_id,
        UploadedFile.file_type == file_type_enum
    ).all()
    
    # Enforce file count limits based on type
    if file_type_enum in [FileType.TRAVELER, FileType.IMAGE]:
        if len(existing_files) >= 1:
            existing_file = existing_files[0]
            raise HTTPException(
                status_code=400,
                detail=f"Only 1 {file_type} file allowed per session. "
                       f"Existing file: '{existing_file.filename}'. "
                       f"Please delete the existing file first or use a different session."
            )
    
    if file_type_enum == FileType.BOM:
        if len(existing_files) >= 4:
            existing_names = [f.filename for f in existing_files]
            raise HTTPException(
                status_code=400,
                detail=f"Maximum 4 BOM files allowed per session. "
                       f"Found {len(existing_files)} existing files: {existing_names}. "
                       f"Please delete an existing BOM file first."
            )
    
    # Validate file extension
    if not validate_file_type(file.filename, file_type_enum):
        allowed = settings.ALLOWED_EXTENSIONS[file_type]
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type for {file_type}. Allowed: {allowed}"
        )
    
    # Check file size
    if file.size and file.size > settings.MAX_UPLOAD_SIZE:
        max_mb = settings.MAX_UPLOAD_SIZE / (1024 * 1024)
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max size: {max_mb:.1f} MB"
        )
    
    # Save file to disk
    storage_path = save_upload_file(file, session_id, file_type_enum)
    
    # Get file size
    file_size = os.path.getsize(storage_path)
    
    # Create database record
    uploaded_file = UploadedFile(
        session_id=session_id,
        filename=file.filename,
        file_type=file_type_enum,
        storage_path=storage_path,
        file_size=file_size,
        processing_status=ProcessingStatus.PENDING
    )
    
    db.add(uploaded_file)
    db.commit()
    db.refresh(uploaded_file)
    
    return uploaded_file

@router.get("/{session_id}/files", response_model=List[FileResponse])
def list_files(
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    List all files for a session
    """
    # Check session exists
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    
    # Get files
    files = db.query(UploadedFile).filter(UploadedFile.session_id == session_id).all()
    
    return files

@router.delete("/{session_id}/files/{file_id}", 
               status_code=204,
               summary="Delete Uploaded File",
               description="""
               Delete a specific uploaded file from a session.
               
               **Use Cases**:
               - Remove duplicate files when upload limit exceeded
               - Clean up incorrectly uploaded files
               - Replace files with updated versions
               
               **Warning**: File deletion is permanent and cannot be undone.
               If analysis is in progress, this may cause validation errors.
               """,
               responses={
                   204: {"description": "File deleted successfully"},
                   404: {"description": "Session or file not found"},
                   409: {"description": "Cannot delete file during analysis"}
               })
def delete_file(
    session_id: str,
    file_id: str,
    db: Session = Depends(get_db)
):
    """Delete a specific file from a session"""
    # Check session exists
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    
    # Check if analysis is in progress
    if session.status == SessionStatus.PROCESSING:
        raise HTTPException(
            status_code=409, 
            detail="Cannot delete files while analysis is in progress"
        )
    
    # Get file
    file_record = db.query(UploadedFile).filter(
        UploadedFile.id == file_id,
        UploadedFile.session_id == session_id
    ).first()
    
    if not file_record:
        raise HTTPException(status_code=404, detail=f"File {file_id} not found in session {session_id}")
    
    # Delete physical file if it exists
    try:
        import os
        if file_record.storage_path and os.path.exists(file_record.storage_path):
            os.remove(file_record.storage_path)
    except Exception as e:
        # Log error but continue with database deletion
        print(f"Warning: Could not delete physical file {file_record.storage_path}: {e}")
    
    # Delete database record
    db.delete(file_record)
    db.commit()
    
    return  # 204 No Content response
