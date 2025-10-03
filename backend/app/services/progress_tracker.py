# app/services/progress_tracker.py
import asyncio
from typing import Dict, Optional, Set
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class ProgressUpdate:
    """Represents a progress update for a session"""
    def __init__(
        self, 
        session_id: str, 
        phase: str, 
        message: str, 
        progress: int,
        status: str = "processing",
        details: Optional[Dict] = None
    ):
        self.session_id = session_id
        self.phase = phase
        self.message = message
        self.progress = progress  # 0-100
        self.status = status  # processing, completed, failed
        self.timestamp = datetime.utcnow().isoformat()
        self.details = details or {}
    
    def to_dict(self):
        return {
            "session_id": self.session_id,
            "phase": self.phase,
            "message": self.message,
            "progress": self.progress,
            "status": self.status,
            "timestamp": self.timestamp,
            "details": self.details
        }


class ProgressTracker:
    """
    Manages progress tracking for validation pipeline.
    Stores progress updates and provides interface for WebSocket broadcasting.
    """
    
    def __init__(self):
        self._progress: Dict[str, ProgressUpdate] = {}
        self._callbacks: Set[callable] = set()
        self._lock = asyncio.Lock()
    
    def register_callback(self, callback: callable):
        """Register a callback to be notified of progress updates"""
        self._callbacks.add(callback)
        logger.debug(f"Registered progress callback. Total callbacks: {len(self._callbacks)}")
    
    def unregister_callback(self, callback: callable):
        """Unregister a callback"""
        self._callbacks.discard(callback)
        logger.debug(f"Unregistered progress callback. Remaining: {len(self._callbacks)}")
    
    async def update(
        self, 
        session_id: str, 
        phase: str, 
        message: str, 
        progress: int,
        status: str = "processing",
        details: Optional[Dict] = None
    ):
        """Update progress for a session and notify callbacks"""
        async with self._lock:
            update = ProgressUpdate(session_id, phase, message, progress, status, details)
            self._progress[session_id] = update
            
            logger.info(f"[Progress] {session_id[:8]}... | {phase} | {progress}% | {message}")
            
            # Notify all registered callbacks (WebSocket connections)
            if self._callbacks:
                for callback in self._callbacks:
                    try:
                        await callback(update.to_dict())
                    except Exception as e:
                        logger.error(f"Error in progress callback: {e}")
    
    def get_progress(self, session_id: str) -> Optional[Dict]:
        """Get current progress for a session"""
        update = self._progress.get(session_id)
        return update.to_dict() if update else None
    
    def clear_progress(self, session_id: str):
        """Clear progress for a session"""
        self._progress.pop(session_id, None)
        logger.debug(f"Cleared progress for session {session_id[:8]}...")


# Global instance
progress_tracker = ProgressTracker()

