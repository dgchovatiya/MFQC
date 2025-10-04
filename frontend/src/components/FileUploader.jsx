import { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Button,
  Typography,
  Paper,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  IconButton,
  Alert,
  CircularProgress,
  Chip,
  Stack,
  LinearProgress,
} from '@mui/material';
import {
  CloudUpload as CloudUploadIcon,
  PictureAsPdf as PdfIcon,
  Image as ImageIcon,
  TableChart as ExcelIcon,
  Delete as DeleteIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  PlayArrow as PlayArrowIcon,
} from '@mui/icons-material';
import { fileAPI, analysisAPI } from '../services/api';

// File type configuration based on API documentation
const FILE_TYPES = {
  traveler: { label: 'Traveler PDF', icon: PdfIcon, accept: '.pdf', limit: 1 },
  image: { label: 'Product Image', icon: ImageIcon, accept: '.jpg,.jpeg,.png', limit: 1 },
  bom: { label: 'BOM Excel', icon: ExcelIcon, accept: '.xlsx,.xlsm', limit: 4 },
};

/**
 * FileUploader Component
 * 
 * Complete file management interface:
 * - Upload files by type with drag-and-drop
 * - Track upload counts vs limits
 * - Show which files are uploaded
 * - Delete files
 * - Enable "Start Analysis" when all requirements met
 */
const FileUploader = ({ sessionId, onFilesUpdate, onAnalysisStart, disabled }) => {
  const [files, setFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  // Load files whenever sessionId changes
  useEffect(() => {
    if (sessionId) {
      loadFiles();
    }
  }, [sessionId]);

  const loadFiles = useCallback(async () => {
    if (!sessionId) return;
    
    try {
      // Use query param false for faster response (no extracted data needed)
      const response = await fileAPI.list(sessionId, false);
      console.log('[FileUploader] API Response:', response);
      
      const filesList = response.files || response || [];
      console.log('[FileUploader] Files array:', filesList);
      console.log('[FileUploader] File types:', filesList.map(f => f.file_type));
      
      setFiles(filesList);
      onFilesUpdate(filesList);
    } catch (err) {
      console.error('[FileUploader] Error loading files:', err);
      setError('Failed to load files');
    }
  }, [sessionId, onFilesUpdate]);

  const handleFileSelect = async (event, fileType) => {
    const selectedFiles = Array.from(event.target.files);
    if (selectedFiles.length > 0) {
      await uploadFiles(selectedFiles, fileType);
      event.target.value = ''; // Clear input
    }
  };

  const uploadFiles = async (filesToUpload, fileType) => {
    setUploading(true);
    setError(null);
    setSuccess(null);

    try {
      for (const file of filesToUpload) {
        console.log(`[FileUploader] Uploading ${file.name} as ${fileType}...`);
        await fileAPI.upload(sessionId, file, fileType);
      }
      
      await loadFiles(); // Refresh file list
      setSuccess(`Successfully uploaded ${filesToUpload.length} ${fileType} file(s)`);
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      setError('Upload failed: ' + (err.response?.data?.detail || err.message));
      console.error('[FileUploader] Upload error:', err);
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (fileId) => {
    setError(null);
    try {
      console.log('[FileUploader] Deleting file:', fileId);
      await fileAPI.delete(sessionId, fileId);
      await loadFiles(); // Refresh file list
      setSuccess('File deleted successfully');
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      setError('Delete failed: ' + (err.response?.data?.detail || err.message));
      console.error('[FileUploader] Delete error:', err);
    }
  };

  const handleStartAnalysis = async () => {
    setError(null);
    try {
      console.log('[FileUploader] Starting analysis for session:', sessionId);
      await analysisAPI.start(sessionId);
      onAnalysisStart();
    } catch (err) {
      setError('Failed to start analysis: ' + (err.response?.data?.detail || err.message));
      console.error('[FileUploader] Analysis start error:', err);
    }
  };

  // Calculate file counts (API returns lowercase file_type)
  const travelerCount = files.filter(f => f.file_type?.toLowerCase() === 'traveler').length;
  const imageCount = files.filter(f => f.file_type?.toLowerCase() === 'image').length;
  const bomCount = files.filter(f => f.file_type?.toLowerCase() === 'bom').length;

  // Check if can start analysis (based on API requirements)
  const canStartAnalysis = travelerCount === 1 && imageCount === 1 && bomCount >= 1 && bomCount <= 4;

  const requirements = {
    traveler: travelerCount === 1,
    image: imageCount === 1,
    bom: bomCount >= 1 && bomCount <= 4,
    all: canStartAnalysis,
  };

  const getFilesByType = (fileType) => {
    return files.filter(f => f.file_type?.toLowerCase() === fileType.toLowerCase());
  };

  const getFileIcon = (fileType) => {
    const Icon = FILE_TYPES[fileType.toLowerCase()]?.icon || PdfIcon;
    return <Icon />;
  };

  return (
    <Box>
      {error && (
        <Alert severity="error" onClose={() => setError(null)} sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {success && (
        <Alert severity="success" onClose={() => setSuccess(null)} sx={{ mb: 2 }}>
          {success}
        </Alert>
      )}

      {/* File Upload Sections */}
      <Stack spacing={2}>
        {Object.entries(FILE_TYPES).map(([fileType, config]) => {
          const filesOfType = getFilesByType(fileType);
          const currentCount = filesOfType.length;
          const isComplete = currentCount >= 1 && currentCount <= config.limit;
          const limitReached = currentCount >= config.limit;

          return (
            <Paper
              key={fileType}
              variant="outlined"
              sx={{
                p: 2,
                borderColor: isComplete ? 'success.main' : 'grey.300',
                bgcolor: 'background.paper',
              }}
            >
              <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
                <Stack direction="row" spacing={1} alignItems="center">
                  <Typography variant="subtitle1" fontWeight="bold">
                    {config.label}
                  </Typography>
                  <Chip
                    label={`${currentCount} / ${config.limit}`}
                    size="small"
                    color={isComplete ? 'success' : 'default'}
                  />
                  {isComplete && <CheckCircleIcon color="success" fontSize="small" />}
                  {limitReached && <Chip label="Limit Reached" color="warning" size="small" />}
                </Stack>

                <Button
                  component="label"
                  variant="outlined"
                  size="small"
                  startIcon={<CloudUploadIcon />}
                  disabled={disabled || uploading || limitReached}
                >
                  Upload
                  <input
                    type="file"
                    hidden
                    accept={config.accept}
                    multiple={config.limit > 1}
                    onChange={(e) => handleFileSelect(e, fileType)}
                  />
                </Button>
              </Stack>

              {filesOfType.length > 0 ? (
                <List dense>
                  {filesOfType.map((file) => (
                    <ListItem
                      key={file.id}
                      secondaryAction={
                        !disabled && (
                          <IconButton
                            edge="end"
                            onClick={() => handleDelete(file.id)}
                            size="small"
                          >
                            <DeleteIcon />
                          </IconButton>
                        )
                      }
                    >
                      <ListItemIcon>{getFileIcon(file.file_type)}</ListItemIcon>
                      <ListItemText
                        primary={file.filename}
                        secondary={`${(file.file_size / 1024).toFixed(1)} KB`}
                      />
                    </ListItem>
                  ))}
                </List>
              ) : (
                <Typography variant="body2" color="text.secondary" sx={{ fontStyle: 'italic', textAlign: 'center', py: 1 }}>
                  No files uploaded yet • Accepts: {config.accept}
                </Typography>
              )}
            </Paper>
          );
        })}
      </Stack>

      {/* Requirements Summary */}
      <Alert severity={requirements.all ? 'success' : 'warning'} sx={{ mt: 2 }}>
        <Typography variant="subtitle2" gutterBottom>
          Upload Requirements:
        </Typography>
        <Stack direction="row" spacing={1} flexWrap="wrap">
          <Chip
            label="1 Traveler PDF"
            color={requirements.traveler ? 'success' : 'default'}
            size="small"
            icon={requirements.traveler ? <CheckCircleIcon /> : <ErrorIcon />}
          />
          <Chip
            label="1 Product Image"
            color={requirements.image ? 'success' : 'default'}
            size="small"
            icon={requirements.image ? <CheckCircleIcon /> : <ErrorIcon />}
          />
          <Chip
            label="1-4 BOM Excel"
            color={requirements.bom ? 'success' : 'default'}
            size="small"
            icon={requirements.bom ? <CheckCircleIcon /> : <ErrorIcon />}
          />
        </Stack>
      </Alert>

      {/* Start Analysis Button */}
      <Box sx={{ mt: 3, textAlign: 'center' }}>
        <Button
          variant="contained"
          size="large"
          color="primary"
          onClick={handleStartAnalysis}
          disabled={!canStartAnalysis || disabled}
          startIcon={<PlayArrowIcon />}
        >
          Start Analysis
        </Button>
        {!canStartAnalysis && !disabled && (
          <Typography variant="caption" display="block" color="text.secondary" sx={{ mt: 1 }}>
            Upload all required files to start analysis
          </Typography>
        )}
      </Box>

      {uploading && <LinearProgress sx={{ mt: 2 }} />}
    </Box>
  );
};

export default FileUploader;

