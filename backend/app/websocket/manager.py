# app/websocket/manager.py
from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, Set
import logging
import json

logger = logging.getLogger(__name__)

class ConnectionManager:
    """
    Manages WebSocket connections for real-time progress updates.
    Supports multiple clients connected to the same session.
    """
    
    def __init__(self):
        # Map: session_id -> Set of WebSocket connections
        self.active_connections: Dict[str, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str):
        """Accept and register a new WebSocket connection"""
        await websocket.accept()
        
        if session_id not in self.active_connections:
            self.active_connections[session_id] = set()
        
        self.active_connections[session_id].add(websocket)
        logger.info(f"[WebSocket] Client connected to session {session_id[:8]}... "
                   f"(Total: {len(self.active_connections[session_id])} clients)")
    
    def disconnect(self, websocket: WebSocket, session_id: str):
        """Remove a WebSocket connection"""
        if session_id in self.active_connections:
            self.active_connections[session_id].discard(websocket)
            
            # Clean up empty session entries
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]
            
            logger.info(f"[WebSocket] Client disconnected from session {session_id[:8]}...")
    
    async def send_to_session(self, session_id: str, message: dict):
        """Send a message to all clients connected to a specific session"""
        if session_id not in self.active_connections:
            return
        
        # Get snapshot of connections (to avoid modification during iteration)
        connections = list(self.active_connections[session_id])
        
        # Send to all connections for this session
        disconnected = []
        for connection in connections:
            try:
                await connection.send_json(message)
            except WebSocketDisconnect:
                disconnected.append(connection)
                logger.warning(f"[WebSocket] Client disconnected during send")
            except Exception as e:
                disconnected.append(connection)
                logger.error(f"[WebSocket] Error sending message: {e}")
        
        # Clean up disconnected clients
        for conn in disconnected:
            self.disconnect(conn, session_id)
    
    async def broadcast_to_all(self, message: dict):
        """Send a message to all connected clients (all sessions)"""
        for session_id in list(self.active_connections.keys()):
            await self.send_to_session(session_id, message)
    
    def get_connection_count(self, session_id: str = None) -> int:
        """Get count of active connections"""
        if session_id:
            return len(self.active_connections.get(session_id, set()))
        return sum(len(conns) for conns in self.active_connections.values())


# Global instance
connection_manager = ConnectionManager()

