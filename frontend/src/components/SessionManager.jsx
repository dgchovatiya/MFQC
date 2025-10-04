import { useState, useEffect } from 'react';
import {
  Box,
  Button,
  Typography,
  Paper,
  List,
  ListItem,
  ListItemText,
  ListItemButton,
  CircularProgress,
  Alert,
  Chip,
  Stack,
  Divider,
} from '@mui/material';
import {
  Add as AddIcon,
  Folder as FolderIcon,
} from '@mui/icons-material';
import { sessionAPI } from '../services/api';

/**
 * SessionManager Component
 * 
 * Handles session creation and selection:
 * - Create new sessions
 * - Display list of recent sessions
 * - Select existing session to continue work
 */
const SessionManager = ({ onSessionSelect, currentSession }) => {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState(null);

  // Load sessions on mount
  useEffect(() => {
    loadSessions();
  }, []);

  const loadSessions = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await sessionAPI.list(0, 10);
      setSessions(response.sessions || []);
      console.log('[SessionManager] Loaded sessions:', response.sessions);
    } catch (err) {
      console.error('[SessionManager] Error loading sessions:', err);
      setError('Failed to load sessions');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateSession = async () => {
    setCreating(true);
    setError(null);
    try {
      const newSession = await sessionAPI.create();
      console.log('[SessionManager] Created session:', newSession);
      onSessionSelect(newSession);
      await loadSessions(); // Refresh list
    } catch (err) {
      console.error('[SessionManager] Error creating session:', err);
      setError('Failed to create session');
    } finally {
      setCreating(false);
    }
  };

  const handleSelectSession = async (session) => {
    setError(null);
    try {
      // Fetch fresh session data
      const freshSession = await sessionAPI.get(session.id);
      console.log('[SessionManager] Selected session:', freshSession);
      onSessionSelect(freshSession);
    } catch (err) {
      console.error('[SessionManager] Error loading session:', err);
      setError('Failed to load session');
    }
  };

  const getStatusColor = (status) => {
    switch (status?.toLowerCase()) {
      case 'completed':
        return 'success';
      case 'processing':
        return 'info';
      case 'failed':
        return 'error';
      default:
        return 'default';
    }
  };

  const getStatusLabel = (status) => {
    return status ? status.toUpperCase() : 'PENDING';
  };

  return (
    <Box>
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
        <Typography variant="h6" fontWeight="bold">
          Session Management
        </Typography>
        <Button
          variant="contained"
          startIcon={creating ? <CircularProgress size={20} color="inherit" /> : <AddIcon />}
          onClick={handleCreateSession}
          disabled={creating}
        >
          {creating ? 'Creating...' : 'New Session'}
        </Button>
      </Stack>

      {error && (
        <Alert severity="error" onClose={() => setError(null)} sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {currentSession && (
        <Paper elevation={2} sx={{ p: 2, mb: 2, bgcolor: 'primary.light', color: 'white' }}>
          <Typography variant="subtitle2" gutterBottom>
            Current Session
          </Typography>
          <Stack direction="row" spacing={2} alignItems="center">
            <FolderIcon />
            <Box sx={{ flexGrow: 1 }}>
              <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                {currentSession.id}
              </Typography>
              <Typography variant="caption">
                Created: {new Date(currentSession.created_at).toLocaleString()}
              </Typography>
            </Box>
            <Chip
              label={getStatusLabel(currentSession.status)}
              color={getStatusColor(currentSession.status)}
              size="small"
            />
          </Stack>
        </Paper>
      )}

      <Divider sx={{ my: 2 }} />

      <Typography variant="subtitle2" color="text.secondary" gutterBottom>
        Recent Sessions
      </Typography>

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
          <CircularProgress />
        </Box>
      ) : sessions.length === 0 ? (
        <Paper variant="outlined" sx={{ p: 3, textAlign: 'center' }}>
          <Typography variant="body2" color="text.secondary">
            No sessions found. Create a new session to get started.
          </Typography>
        </Paper>
      ) : (
        <List sx={{ bgcolor: 'background.paper', borderRadius: 1, border: '1px solid', borderColor: 'divider' }}>
          {sessions.map((session, index) => (
            <ListItem
              key={session.id}
              disablePadding
              divider={index < sessions.length - 1}
            >
              <ListItemButton
                onClick={() => handleSelectSession(session)}
                selected={currentSession?.id === session.id}
              >
                <ListItemText
                  primary={
                    <Stack direction="row" spacing={1} alignItems="center">
                      <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                        {session.id.slice(0, 8)}...
                      </Typography>
                      <Chip
                        label={getStatusLabel(session.status)}
                        color={getStatusColor(session.status)}
                        size="small"
                      />
                      {session.overall_result && (
                        <Chip
                          label={session.overall_result.toUpperCase()}
                          color={getStatusColor(session.overall_result)}
                          size="small"
                          variant="outlined"
                        />
                      )}
                    </Stack>
                  }
                  secondary={`Created: ${new Date(session.created_at).toLocaleString()}`}
                />
              </ListItemButton>
            </ListItem>
          ))}
        </List>
      )}
    </Box>
  );
};

export default SessionManager;

