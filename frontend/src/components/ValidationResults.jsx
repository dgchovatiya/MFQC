import { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Paper,
  Stack,
  Chip,
  Alert,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  CircularProgress,
} from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Warning as WarningIcon,
  Info as InfoIcon,
} from '@mui/icons-material';
import { analysisAPI } from '../services/api';

/**
 * ValidationResults Component
 * 
 * Displays detailed validation results:
 * - Overall status badge
 * - Summary of check counts
 * - Expandable individual checks
 * - Evidence tables with expected vs actual
 * 
 * Based on 7-check validation engine documented in API
 */
const ValidationResults = ({ sessionId }) => {
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (sessionId) {
      fetchResults();
    }
  }, [sessionId]);

  const fetchResults = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await analysisAPI.getResults(sessionId);
      console.log('[ValidationResults] Loaded results:', response);
      setResults(response);
    } catch (err) {
      console.error('[ValidationResults] Error fetching results:', err);
      setError('Failed to load validation results');
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status) => {
    switch (status?.toUpperCase()) {
      case 'PASS':
        return 'success';
      case 'FAIL':
        return 'error';
      case 'WARNING':
        return 'warning';
      case 'INFO':
        return 'info';
      default:
        return 'default';
    }
  };

  const getStatusIcon = (status) => {
    switch (status?.toUpperCase()) {
      case 'PASS':
        return <CheckCircleIcon fontSize="small" />;
      case 'FAIL':
        return <ErrorIcon fontSize="small" />;
      case 'WARNING':
        return <WarningIcon fontSize="small" />;
      case 'INFO':
        return <InfoIcon fontSize="small" />;
      default:
        return null;
    }
  };

  const getStatusSymbol = (status) => {
    switch (status?.toUpperCase()) {
      case 'PASS':
        return '✓';
      case 'FAIL':
        return '✗';
      case 'WARNING':
        return '⚠';
      case 'INFO':
        return 'ℹ';
      default:
        return '•';
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error">
        {error}
      </Alert>
    );
  }

  if (!results || !results.results || results.results.length === 0) {
    return (
      <Alert severity="info">
        No validation results available yet.
      </Alert>
    );
  }

  const { results: checks, overall_status } = results;

  return (
    <Box>
      {/* Overall Status */}
      <Alert
        severity={getStatusColor(overall_status)}
        icon={getStatusIcon(overall_status)}
        sx={{ mb: 3 }}
      >
        <Typography variant="h6" gutterBottom>
          Overall Validation Result: {overall_status?.toUpperCase()}
        </Typography>
        <Typography variant="body2">
          {overall_status === 'PASS' && '✅ All validation checks passed successfully.'}
          {overall_status === 'WARNING' && '⚠️ Validation completed with warnings. Review required.'}
          {overall_status === 'FAIL' && '❌ Critical validation failures detected. Cannot proceed.'}
        </Typography>
      </Alert>

      {/* Validation Summary */}
      <Paper variant="outlined" sx={{ p: 2, mb: 3, bgcolor: 'grey.50' }}>
        <Typography variant="subtitle1" fontWeight="bold" gutterBottom>
          Validation Summary
        </Typography>
        <Stack direction="row" spacing={2} flexWrap="wrap">
          <Chip
            label={`${checks.filter((c) => c.status?.toLowerCase() === 'pass').length} Passed`}
            color="success"
            icon={<CheckCircleIcon />}
            size="small"
          />
          <Chip
            label={`${checks.filter((c) => c.status?.toLowerCase() === 'warning').length} Warnings`}
            color="warning"
            icon={<WarningIcon />}
            size="small"
          />
          <Chip
            label={`${checks.filter((c) => c.status?.toLowerCase() === 'fail').length} Failed`}
            color="error"
            icon={<ErrorIcon />}
            size="small"
          />
          <Chip
            label={`${checks.filter((c) => c.status?.toLowerCase() === 'info').length} Info`}
            color="info"
            icon={<InfoIcon />}
            size="small"
          />
        </Stack>
      </Paper>

      {/* Detailed Check Results */}
      <Typography variant="subtitle1" fontWeight="bold" gutterBottom>
        Detailed Validation Checks
      </Typography>

      <Stack spacing={1}>
        {checks.map((check) => (
          <Accordion key={check.id}>
            <AccordionSummary
              expandIcon={<ExpandMoreIcon />}
              sx={{
                bgcolor:
                  check.status === 'PASS'
                    ? 'success.light'
                    : check.status === 'FAIL'
                    ? 'error.light'
                    : check.status === 'WARNING'
                    ? 'warning.light'
                    : 'info.light',
                '&:hover': {
                  opacity: 0.9,
                },
              }}
            >
              <Stack direction="row" spacing={2} alignItems="center" sx={{ width: '100%' }}>
                <Typography variant="h6" component="span">
                  {getStatusSymbol(check.status)}
                </Typography>
                <Box sx={{ flexGrow: 1 }}>
                  <Typography variant="subtitle1" fontWeight="bold">
                    Check {check.check_priority}: {check.check_name}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {check.message}
                  </Typography>
                </Box>
                <Chip
                  label={check.status?.toUpperCase()}
                  color={getStatusColor(check.status)}
                  size="small"
                  icon={getStatusIcon(check.status)}
                />
              </Stack>
            </AccordionSummary>
            <AccordionDetails>
              <Box>
                <Typography variant="body2" paragraph>
                  <strong>Message:</strong> {check.message}
                </Typography>

                {check.evidence && Object.keys(check.evidence).length > 0 && (
                  <Box sx={{ mt: 2 }}>
                    <Typography variant="subtitle2" gutterBottom>
                      Evidence:
                    </Typography>
                    <TableContainer component={Paper} variant="outlined">
                      <Table size="small">
                        <TableHead>
                          <TableRow>
                            <TableCell>
                              <strong>Field</strong>
                            </TableCell>
                            <TableCell>
                              <strong>Value</strong>
                            </TableCell>
                          </TableRow>
                        </TableHead>
                        <TableBody>
                          {Object.entries(check.evidence).map(([key, value]) => (
                            <TableRow key={key}>
                              <TableCell sx={{ fontFamily: 'monospace' }}>{key}</TableCell>
                              <TableCell>
                                {Array.isArray(value) ? (
                                  <Box component="ul" sx={{ m: 0, pl: 2 }}>
                                    {value.map((item, idx) => (
                                      <li key={idx}>{JSON.stringify(item)}</li>
                                    ))}
                                  </Box>
                                ) : typeof value === 'object' ? (
                                  <pre style={{ margin: 0, fontSize: '0.75rem' }}>
                                    {JSON.stringify(value, null, 2)}
                                  </pre>
                                ) : (
                                  String(value)
                                )}
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </TableContainer>
                  </Box>
                )}

                {(!check.evidence || Object.keys(check.evidence).length === 0) && (
                  <Typography variant="body2" color="text.secondary" sx={{ fontStyle: 'italic' }}>
                    No additional evidence available.
                  </Typography>
                )}
              </Box>
            </AccordionDetails>
          </Accordion>
        ))}
      </Stack>
    </Box>
  );
};

export default ValidationResults;

