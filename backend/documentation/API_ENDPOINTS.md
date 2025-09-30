# Manufacturing QC System - API Documentation

## Overview

The Manufacturing QC Cross-Check System provides REST API endpoints for automating quality control validation of manufacturing documentation. The system processes Traveler PDFs, Product Images, and Excel BOMs to perform comprehensive cross-validation.

## Base URL
```
Local Development: http://localhost:8000
Production: [To be deployed]
```

## Authentication
Currently no authentication required (single-user system).

---

## 📋 Sessions API

### Create Session
**POST** `/api/sessions`

Creates a new analysis session for file uploads and validation.

**Request Body:**
```json
{}
```

**Response:** `201 Created`
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "created_at": "2025-09-29T16:30:00.000Z",
  "updated_at": "2025-09-29T16:30:00.000Z",
  "status": "pending",
  "overall_result": null
}
```

### List Sessions
**GET** `/api/sessions`

Retrieve all sessions with pagination and optional filtering.

**Query Parameters:**
- `skip` (int, default=0): Number of records to skip
- `limit` (int, default=20, max=100): Maximum records to return
- `status` (string, optional): Filter by status (pending/processing/completed/failed)

**Response:** `200 OK`
```json
{
  "sessions": [
    {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "created_at": "2025-09-29T16:30:00.000Z",
      "updated_at": "2025-09-29T16:30:00.000Z",
      "status": "completed",
      "overall_result": "warning"
    }
  ],
  "total": 1
}
```

### Get Session
**GET** `/api/sessions/{session_id}`

Retrieve specific session details.

**Path Parameters:**
- `session_id` (string): Session UUID

**Response:** `200 OK` | `404 Not Found`

### Delete Session
**DELETE** `/api/sessions/{session_id}`

Delete session and all associated files and results.

**Path Parameters:**
- `session_id` (string): Session UUID

**Response:** `204 No Content` | `404 Not Found`

---

## 📁 Files API

### Upload File
**POST** `/api/sessions/{session_id}/files`

Upload a file to a session with type validation.

**Path Parameters:**
- `session_id` (string): Session UUID

**Form Data:**
- `file` (file): The file to upload
- `file_type` (string): Type of file ("traveler", "image", "bom")

**File Type Validation & Limits:**
- **traveler**: .pdf files only - **Maximum 1 per session**
- **image**: .jpg, .jpeg, .png files - **Maximum 1 per session**  
- **bom**: .xlsx, .xlsm files - **Maximum 4 per session**

**File Size Limit:** 10 MB per file

**Upload Constraints:**
- Only 1 traveler PDF allowed per session
- Only 1 product image allowed per session
- Maximum 4 BOM Excel files per session
- Duplicate uploads are rejected with clear error messages

**Response:** `201 Created`
```json
{
  "id": "456e7890-e89b-12d3-a456-426614174001",
  "session_id": "123e4567-e89b-12d3-a456-426614174000",
  "filename": "traveler.pdf",
  "file_type": "traveler",
  "file_size": 2048576,
  "processing_status": "pending",
  "uploaded_at": "2025-09-29T16:31:00.000Z",
  "processed_at": null,
  "extracted_data": null
}
```

**Error Responses:**
- `400 Bad Request`: Invalid file type or extension
- `404 Not Found`: Session not found
- `413 Payload Too Large`: File exceeds size limit

### List Session Files
**GET** `/api/sessions/{session_id}/files`

Retrieve all files uploaded to a session.

**Path Parameters:**
- `session_id` (string): Session UUID

**Response:** `200 OK` | `404 Not Found`
```json
[
  {
    "id": "456e7890-e89b-12d3-a456-426614174001",
    "session_id": "123e4567-e89b-12d3-a456-426614174000",
    "filename": "traveler.pdf",
    "file_type": "traveler",
    "file_size": 2048576,
    "processing_status": "completed",
    "uploaded_at": "2025-09-29T16:31:00.000Z",
    "processed_at": "2025-09-29T16:32:00.000Z",
    "extracted_data": {
      "job_number": "82334",
      "unit_serial": "1619",
      "board_serials": ["80751-0053", "80641-0022"],
      "part_numbers": ["PCA-1153-03", "PCA-1052-05"]
    }
  }
]
```

### Delete File
**DELETE** `/api/sessions/{session_id}/files/{file_id}`

Delete a specific uploaded file from a session.

**Path Parameters:**
- `session_id` (string): Session UUID
- `file_id` (string): File UUID

**Use Cases:**
- Remove duplicate files when upload limit exceeded
- Clean up incorrectly uploaded files  
- Replace files with updated versions

**Response:** `204 No Content` | `404 Not Found` | `409 Conflict`

**Error Responses:**
- `404 Not Found`: Session or file not found
- `409 Conflict`: Cannot delete file during analysis (processing status)

---

## 🔍 Analysis API

### Start Analysis
**POST** `/api/sessions/{session_id}/analyze`

Trigger the validation pipeline for a session.

**Path Parameters:**
- `session_id` (string): Session UUID

**Pre-requisites:**
- Session must have at least:
  - 1 Traveler PDF file
  - 1 Product Image file
  - 1 or more BOM Excel files

**Response:** `202 Accepted`
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "processing",
  "overall_result": null,
  "created_at": "2025-09-29T16:30:00.000Z",
  "updated_at": "2025-09-29T16:33:00.000Z"
}
```

**Error Responses:**
- `400 Bad Request`: Incorrect file counts (examples below)
- `404 Not Found`: Session not found  
- `409 Conflict`: Analysis already in progress or completed

**File Count Error Examples:**
- "Exactly 1 Traveler PDF required, found 2. Please delete duplicates."
- "Exactly 1 Product Image required, found 0"
- "1-4 BOM Excel files required, found 5. Please remove excess BOM files."

### Get Analysis Status
**GET** `/api/sessions/{session_id}/status`

Check the current analysis progress and status.

**Path Parameters:**
- `session_id` (string): Session UUID

**Response:** `200 OK` | `404 Not Found`

**Status Values:**
- `pending`: Session created, ready for file uploads
- `processing`: Analysis pipeline running
- `completed`: Analysis finished, results available
- `failed`: Analysis encountered errors

---

## 📊 Results API

### Get Validation Results
**GET** `/api/sessions/{session_id}/results`

Retrieve all validation results for a completed session.

**Path Parameters:**
- `session_id` (string): Session UUID

**Response:** `200 OK` | `404 Not Found`
```json
{
  "results": [
    {
      "id": "789e0123-e89b-12d3-a456-426614174002",
      "check_name": "Job Number Match",
      "check_priority": 1,
      "status": "pass",
      "message": "Job 82334 found in BOM",
      "evidence": {
        "traveler_job": "82334",
        "bom_jobs": ["82334", "80751", "80641"],
        "match": true
      },
      "created_at": "2025-09-29T16:35:00.000Z"
    },
    {
      "id": "789e0124-e89b-12d3-a456-426614174003", 
      "check_name": "Revision Match: PCA-1153-03",
      "check_priority": 3,
      "status": "warning",
      "message": "PCA-1153-03: Minor revision difference: F vs F2 (same base F)",
      "evidence": {
        "part": "PCA-1153-03",
        "revisions": [
          {"revision": "F", "source": "As_Built_82334.xlsx", "job": "82334"},
          {"revision": "F2", "source": "As_Built_80751.xlsm", "job": "80751"}
        ],
        "comparison": {
          "match": false,
          "type": "minor",
          "message": "Minor revision difference: F vs F2"
        }
      },
      "created_at": "2025-09-29T16:35:01.000Z"
    }
  ],
  "overall_status": "warning"
}
```

**Check Status Values:**
- `pass`: Validation passed
- `warning`: Minor discrepancies detected
- `fail`: Critical issues found
- `info`: Informational notices (e.g., normalization applied)

**Overall Status Hierarchy:**
`FAIL` > `WARNING` > `PASS` > `INFO`

---

## 🔧 System API

### Health Check
**GET** `/health`

System health check endpoint.

**Response:** `200 OK`
```json
{
  "status": "healthy",
  "app": "Manufacturing QC System",
  "version": "1.0.0"
}
```

### Root
**GET** `/`

API root with basic information.

**Response:** `200 OK`
```json
{
  "message": "Welcome to Manufacturing QC System",
  "version": "1.0.0",
  "docs": "/docs",
  "health": "/health"
}
```

---

## 🚀 Typical Workflow

1. **Create Session**
   ```bash
   POST /api/sessions
   ```

2. **Upload Files**
   ```bash
   POST /api/sessions/{id}/files (traveler PDF)
   POST /api/sessions/{id}/files (product image)  
   POST /api/sessions/{id}/files (BOM excel files)
   ```

3. **Start Analysis**
   ```bash
   POST /api/sessions/{id}/analyze
   ```

4. **Monitor Progress**
   ```bash
   GET /api/sessions/{id}/status
   ```

5. **Retrieve Results**
   ```bash
   GET /api/sessions/{id}/results
   ```

---

## ⚠️ Error Handling

All endpoints return appropriate HTTP status codes:

- `200 OK`: Successful GET requests
- `201 Created`: Successful POST requests that create resources
- `202 Accepted`: Request accepted for background processing
- `204 No Content`: Successful DELETE requests
- `400 Bad Request`: Invalid request data or missing requirements
- `404 Not Found`: Resource not found
- `409 Conflict`: Resource conflict (e.g., duplicate processing)
- `413 Payload Too Large`: File size exceeds limit

Error responses include detailed messages:
```json
{
  "detail": "Job 82334 not found in any BOM"
}
```
