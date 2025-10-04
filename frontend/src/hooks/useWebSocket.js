import { useState, useEffect, useCallback, useRef } from 'react';
import { getWebSocketURL } from '../services/api';

/**
 * Custom React hook for WebSocket real-time progress updates
 * 
 * Connects to backend WebSocket endpoint and receives live analysis progress.
 * Handles reconnection, error states, and provides clean state management.
 * 
 * @param {string} sessionId - Session ID to monitor
 * @param {boolean} enabled - Whether to establish connection
 * @returns {object} WebSocket state and helper functions
 */
export const useWebSocket = (sessionId, enabled = true) => {
  const [progress, setProgress] = useState(0);
  const [phase, setPhase] = useState('');
  const [message, setMessage] = useState('');
  const [status, setStatus] = useState('disconnected');
  const [details, setDetails] = useState({});
  const [error, setError] = useState(null);
  
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const reconnectAttemptsRef = useRef(0);
  const maxReconnectAttempts = 5;

  const connect = useCallback(() => {
    if (!sessionId || !enabled) return;

    try {
      const wsURL = getWebSocketURL(sessionId);
      console.log('[WebSocket] Connecting to:', wsURL);
      
      const ws = new WebSocket(wsURL);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('[WebSocket] Connected successfully');
        setStatus('connected');
        setError(null);
        reconnectAttemptsRef.current = 0;
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log('[WebSocket] Progress update:', data);

          setProgress(data.progress || 0);
          setPhase(data.phase || '');
          setMessage(data.message || '');
          setStatus(data.status || 'processing');
          setDetails(data.details || {});
          setError(null);
        } catch (err) {
          console.error('[WebSocket] Parse error:', err);
          setError('Failed to parse server message');
        }
      };

      ws.onerror = (event) => {
        console.error('[WebSocket] Connection error:', event);
        setError('WebSocket connection error');
        setStatus('error');
      };

      ws.onclose = (event) => {
        console.log('[WebSocket] Connection closed:', event.code, event.reason);
        setStatus('disconnected');
        wsRef.current = null;

        // Attempt reconnection if not a clean closure
        if (event.code !== 1000 && reconnectAttemptsRef.current < maxReconnectAttempts && enabled) {
          reconnectAttemptsRef.current += 1;
          const delay = Math.min(1000 * Math.pow(2, reconnectAttemptsRef.current), 10000);
          console.log(`[WebSocket] Reconnecting in ${delay}ms (attempt ${reconnectAttemptsRef.current})`);
          
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, delay);
        }
      };
    } catch (err) {
      console.error('[WebSocket] Connection failed:', err);
      setError(err.message);
      setStatus('error');
    }
  }, [sessionId, enabled]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    
    if (wsRef.current) {
      wsRef.current.close(1000, 'Client disconnect');
      wsRef.current = null;
    }
    
    setStatus('disconnected');
  }, []);

  // Connect on mount or when dependencies change
  useEffect(() => {
    if (enabled && sessionId) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [sessionId, enabled, connect, disconnect]);

  return {
    progress,
    phase,
    message,
    status,
    details,
    error,
    isConnected: status === 'connected' || status === 'processing',
    isProcessing: status === 'processing',
    isCompleted: status === 'completed',
    isFailed: status === 'failed',
    reconnect: connect,
    disconnect,
  };
};

export default useWebSocket;

