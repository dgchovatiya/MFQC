import { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  LinearProgress,
  Paper,
  Stack,
  Chip,
  Alert,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Divider,
} from '@mui/material';
import {
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  RadioButtonUnchecked as PendingIcon,
  PlayArrow as ActiveIcon,
  Warning as WarningIcon,
  Info as InfoIcon,
} from '@mui/icons-material';
import { useWebSocket } from '../hooks/useWebSocket';

/**
 * ProgressMonitor Component
 * 
 * Real-time analysis progress monitoring with:
 * - Overall progress bar (0-100%)
 * - Phase-by-phase status table
 * - Live validation check results (granular updates)
 * - Live WebSocket updates
 * - Connection status indicator
 * 
 * Based on 5-phase pipeline with granular Phase 9 updates
 */
const ProgressMonitor = ({ sessionId, onAnalysisComplete }) => {
  const {
    progress,
    phase,
    message,
    status,
    details,
    error,
    isConnected,
    isCompleted,
    isFailed,
  } = useWebSocket(sessionId, true);

  // State for live validation check results
  const [liveCheckResults, setLiveCheckResults] = useState([]);

  // Notify parent when analysis completes
  useEffect(() => {
    if ((isCompleted || isFailed) && onAnalysisComplete) {
      console.log('[ProgressMonitor] Analysis completed, notifying parent');
      onAnalysisComplete(status);
    }
  }, [isCompleted, isFailed, status, onAnalysisComplete]);

  // Capture individual validation check results from WebSocket details
  useEffect(() => {
    if (details && details.check_name && details.check_status) {
      // This is a granular validation check update
      const checkResult = {
        check_number: details.check_number,
        check_name: details.check_name,
        status: details.check_status,
        message: details.check_message,
        expected_value: details.expected_value,
        actual_value: details.actual_value,
        check_details: details.check_details,
        timestamp: new Date().toISOString(),
        unique_id: `${details.check_number}-${Date.now()}-${Math.random()}`, // Unique ID for each check instance
      };

      console.log('[ProgressMonitor] Live check result:', checkResult);

      // Add to live results - ALWAYS accumulate (allow multiple entries per check_number)
      // Each validation check can have multiple results (e.g., Check 2 for multiple part numbers)
      setLiveCheckResults((prev) => {
        // Extract unique identifier based on check type
        let uniqueIdentifier = null;
        
        if (details.check_number === 1) {
          // Job Number
          uniqueIdentifier = details.check_details?.job_number || details.expected_value;
        } else if (details.check_number === 2) {
          // Part Number
          uniqueIdentifier = details.check_details?.part_number || details.expected_value;
        } else if (details.check_number === 3) {
          // Revision
          uniqueIdentifier = `${details.check_details?.part_number}-${details.check_details?.source_revision}`;
        } else if (details.check_number === 4) {
          // Board Serial
          uniqueIdentifier = details.check_details?.serial || details.expected_value;
        } else if (details.check_number === 5) {
          // Unit Serial
          uniqueIdentifier = details.check_details?.unit_serial || details.expected_value;
        } else if (details.check_number === 6) {
          // Flight Status
          uniqueIdentifier = details.check_details?.flight_status || 'flight-status';
        } else if (details.check_number === 7) {
          // File Completeness
          uniqueIdentifier = 'file-completeness';
        }
        
        // Check if this specific item already exists
        const exists = prev.find(
          (c) => 
            c.check_number === checkResult.check_number &&
            c.expected_value === checkResult.expected_value &&
            c.message === checkResult.message
        );
        
        if (exists) {
          // Update existing check (status might change)
          return prev.map((c) =>
            c.check_number === checkResult.check_number &&
            c.expected_value === checkResult.expected_value &&
            c.message === checkResult.message
              ? checkResult
              : c
          );
        }
        
        // Add as new check entry
        return [...prev, checkResult];
      });
    }
  }, [details]);

  // Clear live checks ONLY when starting new analysis (progress = 0)
  // Don't clear on disconnect after completion
  useEffect(() => {
    if (progress === 0) {
      setLiveCheckResults([]);
    }
  }, [progress]);

  // Pipeline phases with progress ranges
  const phases = [
    {
      id: 1,
      name: 'PDF Parsing',
      fullName: 'Phase 1-5: PDF Parsing',
      range: [0, 20],
      description: 'Extracting data from Traveler PDF',
    },
    {
      id: 2,
      name: 'Image OCR',
      fullName: 'Phase 6: Image OCR',
      range: [20, 45],
      description: 'Analyzing product image with OCR',
    },
    {
      id: 3,
      name: 'Excel BOM Parsing',
      fullName: 'Phase 7: Excel BOM Parsing',
      range: [45, 70],
      description: 'Processing Excel BOM files',
    },
    {
      id: 4,
      name: 'Data Normalization',
      fullName: 'Phase 8: Data Normalization',
      range: [70, 85],
      description: 'Normalizing and standardizing data',
    },
    {
      id: 5,
      name: 'Validation Engine',
      fullName: 'Phase 9: Validation Engine',
      range: [85, 100],
      description: 'Running 7-check validation',
    },
  ];

  // Determine phase status based on progress
  const getPhaseStatus = (phaseRange) => {
    if (progress >= phaseRange[1]) return 'completed';
    if (progress >= phaseRange[0] && progress < phaseRange[1]) return 'active';
    return 'pending';
  };

  // Get status icon for phase
  const getPhaseStatusIcon = (phaseStatus) => {
    if (phaseStatus === 'completed') {
      return <CheckCircleIcon fontSize="small" color="success" />;
    } else if (phaseStatus === 'active') {
      return <ActiveIcon fontSize="small" color="primary" />;
    }
    return <PendingIcon fontSize="small" color="disabled" />;
  };

  // Get status color for phase row
  const getPhaseRowColor = (phaseStatus) => {
    if (phaseStatus === 'completed') return 'success.light';
    if (phaseStatus === 'active') return 'primary.light';
    return 'transparent';
  };

  const getStatusColor = () => {
    if (isCompleted) return 'success';
    if (isFailed) return 'error';
    return 'info';
  };

  const getStatusIcon = () => {
    if (isCompleted) return <CheckCircleIcon />;
    if (isFailed) return <ErrorIcon />;
    return <ActiveIcon />;
  };

  return (
    <Box>
      {/* Connection Status */}
      {!isConnected && !error && status !== 'completed' && (
        <Alert severity="info" sx={{ mb: 2 }}>
          🔌 Connecting to real-time progress stream...
        </Alert>
      )}

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          ⚠️ {error}
        </Alert>
      )}

      {/* Overall Progress Bar */}
      <Paper elevation={2} sx={{ p: 3, mb: 3 }}>
        <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
          <Typography variant="h6" fontWeight="bold">
            {phase || 'Initializing...'}
          </Typography>
          <Chip
            label={`${progress}%`}
            color={getStatusColor()}
            icon={getStatusIcon()}
            size="medium"
            sx={{ fontSize: '1rem', fontWeight: 'bold' }}
          />
        </Stack>

        <LinearProgress
          variant="determinate"
          value={progress}
          sx={{
            height: 12,
            borderRadius: 6,
            '& .MuiLinearProgress-bar': {
              borderRadius: 6,
              bgcolor: isCompleted ? 'success.main' : isFailed ? 'error.main' : 'primary.main',
              transition: 'width 0.5s ease-in-out',
            },
          }}
        />

        <Typography variant="body1" color="text.secondary" sx={{ mt: 1.5 }}>
          {message || 'Waiting for updates...'}
        </Typography>
      </Paper>

      {/* Pipeline Phases Status Table */}
      <TableContainer component={Paper} elevation={2} sx={{ mb: 3 }}>
        <Table size="small">
          <TableHead>
            <TableRow sx={{ bgcolor: 'grey.100' }}>
              <TableCell sx={{ fontWeight: 'bold', width: '80px' }}>Status</TableCell>
              <TableCell sx={{ fontWeight: 'bold' }}>Phase</TableCell>
              <TableCell sx={{ fontWeight: 'bold' }}>Description</TableCell>
              <TableCell align="center" sx={{ fontWeight: 'bold', width: '100px' }}>
                Progress
              </TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {phases.map((phaseInfo) => {
              const phaseStatus = getPhaseStatus(phaseInfo.range);
              const phaseProgress =
                phaseStatus === 'completed'
                  ? 100
                  : phaseStatus === 'active'
                  ? Math.round(
                      ((progress - phaseInfo.range[0]) / (phaseInfo.range[1] - phaseInfo.range[0])) * 100
                    )
                  : 0;

              return (
                <TableRow
                  key={phaseInfo.id}
                  sx={{
                    bgcolor: getPhaseRowColor(phaseStatus),
                    '&:hover': {
                      bgcolor: phaseStatus === 'active' ? 'primary.lighter' : undefined,
                    },
                    transition: 'background-color 0.3s',
                  }}
                >
                  <TableCell>
                    <Stack direction="row" spacing={0.5} alignItems="center">
                      {getPhaseStatusIcon(phaseStatus)}
                    </Stack>
                  </TableCell>
                  <TableCell>
                    <Typography
                      variant="body2"
                      sx={{
                        fontWeight: phaseStatus === 'active' ? 'bold' : 'normal',
                        color:
                          phaseStatus === 'completed'
                            ? 'success.dark'
                            : phaseStatus === 'active'
                            ? 'primary.dark'
                            : 'text.secondary',
                      }}
                    >
                      {phaseInfo.name}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography
                      variant="body2"
                      color={phaseStatus === 'active' ? 'text.primary' : 'text.secondary'}
                    >
                      {phaseInfo.description}
                    </Typography>
                  </TableCell>
                  <TableCell align="center">
                    <Chip
                      label={phaseStatus === 'completed' ? '✓' : `${phaseProgress}%`}
                      size="small"
                      color={
                        phaseStatus === 'completed'
                          ? 'success'
                          : phaseStatus === 'active'
                          ? 'primary'
                          : 'default'
                      }
                      sx={{ minWidth: 50 }}
                    />
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </TableContainer>

      

      {/* Completion/Failure Messages */}
      {isCompleted && (
        <Alert severity="success" icon={<CheckCircleIcon />}>
          <Typography variant="body1" fontWeight="bold">
            ✅ Analysis Complete!
          </Typography>
          <Typography variant="body2">
            All validation checks have been completed. Detailed results are displayed below.
          </Typography>
        </Alert>
      )}

      {isFailed && (
        <Alert severity="error" icon={<ErrorIcon />}>
          <Typography variant="body1" fontWeight="bold">
            ❌ Analysis Failed
          </Typography>
          <Typography variant="body2">
            {message || 'An error occurred during processing. Please review the error details or try again.'}
          </Typography>
        </Alert>
      )}

      {/* Real-time Connection Indicator */}
      {isConnected && !isCompleted && !isFailed && (
        <Stack direction="row" spacing={1} alignItems="center" sx={{ mt: 2 }}>
          <Box
            sx={{
              width: 8,
              height: 8,
              borderRadius: '50%',
              bgcolor: 'success.main',
              animation: 'pulse 2s ease-in-out infinite',
              '@keyframes pulse': {
                '0%, 100%': { opacity: 1 },
                '50%': { opacity: 0.5 },
              },
            }}
          />
          <Typography variant="caption" color="text.secondary">
            Real-time updates active
          </Typography>
        </Stack>
      )}
    </Box>
  );
};

export default ProgressMonitor;

