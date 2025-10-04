import axios from 'axios';

// API Base URL - uses environment variable or defaults to localhost
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Create axios instance with default config
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// ========== SESSION API ==========
export const sessionAPI = {
  // Create new session
  create: async () => {
    const response = await api.post('/api/sessions', {});
    return response.data;
  },

  // List all sessions
  list: async (skip = 0, limit = 20) => {
    const response = await api.get('/api/sessions', {
      params: { skip, limit }
    });
    return response.data;
  },

  // Get session by ID
  get: async (sessionId) => {
    const response = await api.get(`/api/sessions/${sessionId}`);
    return response.data;
  },
};

// ========== FILE API ==========
export const fileAPI = {
  // Upload file
  upload: async (sessionId, file, fileType) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('file_type', fileType);

    const response = await api.post(
      `/api/sessions/${sessionId}/files`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );
    return response.data;
  },

  // List files for session (with optional query param for extracted data)
  list: async (sessionId, includeExtractedData = false) => {
    const response = await api.get(`/api/sessions/${sessionId}/files`, {
      params: { include_extracted_data: includeExtractedData }
    });
    return response.data;
  },

  // Delete file
  delete: async (sessionId, fileId) => {
    await api.delete(`/api/sessions/${sessionId}/files/${fileId}`);
  },
};

// ========== ANALYSIS API ==========
export const analysisAPI = {
  // Start analysis
  start: async (sessionId) => {
    const response = await api.post(`/api/sessions/${sessionId}/analyze`);
    return response.data;
  },

  // Get results
  getResults: async (sessionId) => {
    const response = await api.get(`/api/sessions/${sessionId}/results`);
    return response.data;
  },
};

// ========== WEBSOCKET URL HELPER ==========
export const getWebSocketURL = (sessionId) => {
  const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsHost = import.meta.env.VITE_WS_URL || `${wsProtocol}//${window.location.hostname}:8000`;
  return `${wsHost}/api/ws/${sessionId}/progress`;
};

export default api;
