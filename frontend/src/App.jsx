import { useState } from 'react';
import {
  Container,
  AppBar,
  Toolbar,
  Typography,
  Box,
  Paper,
  CssBaseline,
  ThemeProvider,
  Divider,
} from '@mui/material';
import {
  Science as ScienceIcon,
} from '@mui/icons-material';
import theme from './theme/theme';
import SessionManager from './components/SessionManager';
import FileUploader from './components/FileUploader';
import ProgressMonitor from './components/ProgressMonitor';
import ValidationResults from './components/ValidationResults';

/**
 * Main Application Component
 * 
 * Orchestrates the entire QC workflow:
 * 1. Session creation/selection
 * 2. File uploads (traveler, image, BOM)
 * 3. Analysis execution
 * 4. Real-time progress monitoring
 * 5. Validation results display
 */
function App() {
  const [currentSession, setCurrentSession] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisCompleted, setAnalysisCompleted] = useState(false);
  const [resultsKey, setResultsKey] = useState(0); // Key to force ValidationResults refresh

  const handleSessionSelect = (session) => {
    console.log('[App] Session selected:', session);
    
    const isCompleted = session.status?.toLowerCase() == 'completed';
    const isProcessing = session.status?.toLowerCase() == 'processing';
    
    // If selecting a different session or re-selecting completed session, refresh results
    if (session.id !== currentSession?.id || isCompleted) {
      console.log('[App] Incrementing results key for session:', session.id);
      setResultsKey(prev => prev + 1);
    }
    
    // Update session state
    setCurrentSession(session);
    setIsAnalyzing(isProcessing);
    setAnalysisCompleted(isCompleted);
  };

  const handleFilesUpdate = (files) => {
    console.log('[App] Files updated:', files.length);
  };

  const handleAnalysisStart = () => {
    console.log('[App] Analysis started for session:', currentSession?.id);
    setIsAnalyzing(true);
    setAnalysisCompleted(false);
  };

  const handleAnalysisComplete = (status) => {
    console.log('[App] Analysis completed with status:', status);
    setIsAnalyzing(false);
    setAnalysisCompleted(true);
  };

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box sx={{ flexGrow: 1, minHeight: '100vh', bgcolor: 'background.default' }}>
        {/* App Bar */}
        <AppBar position="static" elevation={2}>
          <Toolbar>
            <ScienceIcon sx={{ mr: 2 }} />
            <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
              Manufacturing QC System
            </Typography>
            {currentSession && (
              <Typography variant="body2" sx={{ fontFamily: 'monospace', mr: 2 }}>
                Session: {currentSession.id.slice(0, 8)}...
              </Typography>
            )}
          </Toolbar>
        </AppBar>

        {/* Main Content */}
        <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
          {/* Step 1: Session Management */}
          <Paper elevation={3} sx={{ p: 3, mb: 3 }}>
            <Typography variant="h6" gutterBottom>
              Step 1: Session Management
            </Typography>
            <Divider sx={{ mb: 2 }} />
            <SessionManager
              onSessionSelect={handleSessionSelect}
              currentSession={currentSession}
            />
          </Paper>

          {/* Only show workflow if session is selected */}
          {currentSession && (
            <>
              {/* Step 2: File Upload (hide for completed/processing sessions) */}
              {!isAnalyzing && !analysisCompleted && (
                <Paper elevation={3} sx={{ p: 3, mb: 3 }}>
                  <Typography variant="h6" gutterBottom>
                    Step 2: Upload Files
                  </Typography>
                  <Divider sx={{ mb: 2 }} />
                  <FileUploader
                    sessionId={currentSession.id}
                    onFilesUpdate={handleFilesUpdate}
                    onAnalysisStart={handleAnalysisStart}
                    disabled={isAnalyzing}
                  />
                </Paper>
              )}

              {/* Step 2: Validation Results (for completed sessions) */}
              {analysisCompleted && (
                <Paper elevation={3} sx={{ p: 3, mb: 3 }}>
                  <Typography variant="h6" gutterBottom>
                    Step 2: Validation Results
                  </Typography>
                  <Divider sx={{ mb: 2 }} />
                  <ValidationResults 
                    key={resultsKey} 
                    sessionId={currentSession.id} 
                  />
                </Paper>
              )}

              {/* Step 3: Analysis Progress (show during analysis only) */}
              {isAnalyzing && (
                <Paper elevation={3} sx={{ p: 3, mb: 3 }}>
                  <Typography variant="h6" gutterBottom>
                    Step 3: Analysis in Progress
                  </Typography>
                  <Divider sx={{ mb: 2 }} />
                  <ProgressMonitor 
                    sessionId={currentSession.id} 
                    onAnalysisComplete={handleAnalysisComplete}
                  />
                </Paper>
              )}
            </>
          )}

          {/* Instructions */}
          {!currentSession && (
            <Paper elevation={1} sx={{ p: 3, bgcolor: 'info.light' }}>
              <Typography variant="h6" gutterBottom>
                Welcome to Manufacturing QC System
              </Typography>
              <Typography variant="body1" paragraph>
                This system automates manufacturing documentation validation by cross-checking:
              </Typography>
              <Typography component="ul" variant="body2" sx={{ pl: 2 }}>
                <li>Traveler PDF documents</li>
                <li>Product hardware images</li>
                <li>Excel Bill of Materials (BOM) files</li>
              </Typography>
              <Typography variant="body1" sx={{ mt: 2 }}>
                <strong>To get started:</strong> Create a new session or select an existing one above.
              </Typography>
            </Paper>
          )}
        </Container>

        {/* Footer */}
        <Box
          component="footer"
          sx={{
            py: 3,
            px: 2,
            mt: 'auto',
            bgcolor: 'background.paper',
            borderTop: 1,
            borderColor: 'divider',
          }}
        >
          <Container maxWidth="xl">
            <Typography variant="body2" color="text.secondary" align="center">
              Manufacturing QC System v1.0.0 | Automated Quality Control Validation
            </Typography>
          </Container>
        </Box>
      </Box>
    </ThemeProvider>
  );
}

export default App;

