# app/api/websocket.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.session import Session as SessionModel
from ..websocket.manager import connection_manager
from ..services.progress_tracker import progress_tracker
from ..logging_config import setup_logging
import logging

logger = setup_logging()

router = APIRouter()

@router.websocket("/{session_id}/progress")
async def websocket_progress(
    websocket: WebSocket,
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    WebSocket endpoint for real-time progress updates.
    
    Connect to this endpoint to receive live updates during validation pipeline:
    - Phase start/completion notifications
    - Progress percentage (0-100)
    - Status messages (processing, completed, failed)
    - Detailed phase information
    
    Message format:
    {
        "session_id": "123e4567-e89b-12d3-a456-426614174000",
        "phase": "Phase 6: Image OCR",
        "message": "Processing white labels...",
        "progress": 65,
        "status": "processing",
        "timestamp": "2025-10-03T12:34:56.789Z",
        "details": {...}
    }
    """
    # Verify session exists
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        await websocket.close(code=4004, reason=f"Session {session_id} not found")
        return
    
    # Connect WebSocket
    await connection_manager.connect(websocket, session_id)
    
    logger.info(f"[WebSocket] Client connected to session {session_id[:8]}...")
    
    try:
        # Send current progress if available
        current_progress = progress_tracker.get_progress(session_id)
        if current_progress:
            await websocket.send_json(current_progress)
        else:
            # Send initial connection message
            await websocket.send_json({
                "session_id": session_id,
                "phase": "Connection",
                "message": "Connected to progress stream",
                "progress": 0,
                "status": "connected",
                "timestamp": None,
                "details": {}
            })
        
        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Wait for messages from client (ping/pong or control messages)
                data = await websocket.receive_text()
                
                # Handle client messages (optional - for ping/pong)
                if data == "ping":
                    await websocket.send_json({"type": "pong"})
                elif data == "get_progress":
                    current = progress_tracker.get_progress(session_id)
                    if current:
                        await websocket.send_json(current)
                
            except WebSocketDisconnect:
                logger.info(f"[WebSocket] Client disconnected from session {session_id[:8]}...")
                break
            except Exception as e:
                logger.error(f"[WebSocket] Error receiving message: {e}")
                break
    
    finally:
        # Clean up connection
        connection_manager.disconnect(websocket, session_id)

