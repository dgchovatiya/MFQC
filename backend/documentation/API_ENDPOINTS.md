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

Retrieve all files uploaded to a session with optional extracted data.

**Path Parameters:**

- `session_id` (string): Session UUID

**Query Parameters:**

- `include_extracted_data` (boolean, default=false): Include extracted OCR/parsed data in response

**Performance Optimization:**

- **Default behavior** (include_extracted_data=false): Returns lightweight file metadata for quick tracking
- **With extracted data** (include_extracted_data=true): Returns complete file details including large JSON extraction results

**Use Cases:**

- **File Tracking UI**: Use default endpoint for fast file list display
- **File Detail View**: Use include_extracted_data=true to show OCR/parsed content

**Response:** `200 OK` | `404 Not Found`

**Basic Response (Default):**

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
    "processed_at": "2025-09-29T16:32:00.000Z"
  }
]
```

**With Extracted Data (include_extracted_data=true):**

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

**Examples:**

```bash
# Quick file list (default - faster)
GET /api/sessions/{session_id}/files

# Complete file details with OCR/parsed data
GET /api/sessions/{session_id}/files?include_extracted_data=true
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
      "check_name": "Job Number",
      "check_priority": 1,
      "status": "pass",
      "message": "Job number 82334 found in 1 Excel file(s)",
      "expected_value": "Job 82334 in Excel BOMs",
      "actual_value": "Found in: REDACTED_As Built 82334 INF-1619.xlsx",
      "evidence": {
        "job_number": "82334",
        "found_in_bom": true,
        "bom_files": ["REDACTED_As Built 82334 INF-1619.xlsx"]
      },
      "created_at": "2025-09-29T16:35:00.000Z"
    },
    {
      "id": "789e0124-e89b-12d3-a456-426614174003", 
      "check_name": "Part Number",
      "check_priority": 2,
      "status": "pass",
      "message": "Part number PCA-1153-03 found in Excel BOMs",
      "expected_value": "PCA-1153-03",
      "actual_value": "Found in: Excel BOM files",
      "evidence": {
        "part_number": "PCA-1153-03",
        "source": ["traveler", "image"],
        "found_in_bom": true
      },
      "created_at": "2025-09-29T16:35:01.000Z"
    },
    {
      "id": "789e0125-e89b-12d3-a456-426614174004",
      "check_name": "Part Number",
      "check_priority": 2,
      "status": "fail",
      "message": "Part number PCA-1130-03 from traveler not found in any Excel BOMs",
      "expected_value": "PCA-1130-03",
      "actual_value": "Not found in BOM files",
      "evidence": {
        "part_number": "PCA-1130-03",
        "source": ["traveler"],
        "found_in_bom": false
      },
      "created_at": "2025-09-29T16:35:02.000Z"
    },
    {
      "id": "789e0126-e89b-12d3-a456-426614174005",
      "check_name": "Revision",
      "check_priority": 3,
      "status": "warning",
      "message": "Revision mismatch for PCA-1052-05: Excel shows 'F2' but image shows 'F'",
      "expected_value": "PCA-1052-05 Rev F",
      "actual_value": "Excel shows: 'F2'",
      "evidence": {
        "part_number": "PCA-1052-05",
        "source_revision": "F",
        "bom_revisions": ["F2"],
        "match": false,
        "minor_difference": true
      },
      "created_at": "2025-09-29T16:35:03.000Z"
    },
    {
      "id": "789e0127-e89b-12d3-a456-426614174006",
      "check_name": "Board Serial",
      "check_priority": 4,
      "status": "pass",
      "message": "Board PCA-1153-03 serial matches: VGN-80751-0053 (image) = VGN-80751-0053 (traveler without prefix)",
      "expected_value": "VGN-80751-0053",
      "actual_value": "VGN-80751-0053 (matched)",
      "evidence": {
        "serial": "VGN-80751-0053",
        "part_number": "PCA-1153-03",
        "normalized": true,
        "in_traveler": true,
        "in_image": true
      },
      "created_at": "2025-09-29T16:35:04.000Z"
    },
    {
      "id": "789e0128-e89b-12d3-a456-426614174007",
      "check_name": "Unit Serial",
      "check_priority": 5,
      "status": "pass",
      "message": "Unit serial matches: INF-1619 (image) = INF-1619 (traveler without prefix)",
      "expected_value": "INF-1619",
      "actual_value": "INF-1619 (matched)",
      "evidence": {
        "unit_serial": "INF-1619",
        "normalized": true,
        "in_traveler": true,
        "in_image": true
      },
      "created_at": "2025-09-29T16:35:05.000Z"
    }
  ],
  "overall_status": "warning"
}
```

**Key Features:**
- **Individual checks**: Multiple results per check type (e.g., one per part number)
- **Expected vs Actual**: Clear comparison fields for UI display
- **Detailed evidence**: Additional metadata in JSON format
- **Status hierarchy**: fail > warning > pass > info

**Check Status Values:**

- `pass`: Validation passed
- `warning`: Minor discrepancies detected
- `fail`: Critical issues found
- `info`: Informational notices (e.g., normalization applied)

**Overall Status Hierarchy:**
`FAIL` > `WARNING` > `PASS` > `INFO`

---

## 🔌 WebSocket API

### Real-Time Progress Updates

**WebSocket** `ws://localhost:8000/api/ws/{session_id}/progress`

Connect to receive real-time progress updates during validation pipeline execution.

**Path Parameters:**

- `session_id` (string): Session UUID

**Connection Behavior:**

- Automatically sends current progress upon connection
- Streams live updates as analysis progresses
- Supports multiple clients per session
- Gracefully handles disconnections

**Message Format:**
All progress messages follow this structure:

```json
{
  "session_id": "123e4567-e89b-12d3-a456-426614174000",
  "phase": "Phase 6: Image OCR",
  "message": "Processing white labels...",
  "progress": 45,
  "status": "processing",
  "timestamp": "2025-10-04T12:34:56.789Z",
  "details": {}
}
```

**Message Fields:**

- `session_id` (string): Session being processed
- `phase` (string): Current pipeline phase name
- `message` (string): Human-readable status message
- `progress` (number, 0-100): Overall completion percentage
- `status` (string): Current status - see values below
- `timestamp` (string, ISO 8601): Message timestamp
- `details` (object): Additional phase-specific information

**Status Values:**

- `connected`: WebSocket connection established
- `processing`: Analysis in progress
- `completed`: Analysis finished successfully
- `failed`: Analysis encountered errors


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
   # Response: { "id": "session-uuid", "status": "pending", ... }
   ```
2. **Upload Files**

   ```bash
   POST /api/sessions/{id}/files (traveler PDF)
   POST /api/sessions/{id}/files (product image)  
   POST /api/sessions/{id}/files (BOM excel files)
   ```
3. **List Files (Optional)**

   ```bash
   # Quick file tracking
   GET /api/sessions/{id}/files

   # With extracted data
   GET /api/sessions/{id}/files?include_extracted_data=true
   ```
4. **Start Analysis**

   ```bash
   POST /api/sessions/{id}/analyze
   # Response: 202 Accepted - Analysis started in background
   ```
5. **Monitor Progress (Two Options)**

   **Option A: WebSocket (Recommended - Real-time)**

   ```javascript
   // Connect to WebSocket for live updates
   const ws = new WebSocket('ws://localhost:8000/api/ws/{id}/progress');
   ws.onmessage = (event) => {
     const update = JSON.parse(event.data);
     console.log(`Progress: ${update.progress}% - ${update.message}`);
   };
   ```

   **Option B: Polling (HTTP)**

   ```bash
   # Poll for status updates
   GET /api/sessions/{id}/status
   ```
6. **Retrieve Results**

   ```bash
   GET /api/sessions/{id}/results
   # Response: Complete validation results with evidence
   ```

### Workflow Example with WebSocket

```javascript
// 1. Create session
const session = await createSession();

// 2. Upload files
await uploadFile(session.id, travelerPdf, 'traveler');
await uploadFile(session.id, productImage, 'image');
await uploadFile(session.id, bomFile, 'bom');

// 3. Connect WebSocket before starting analysis
const ws = new WebSocket(`ws://localhost:8000/api/ws/${session.id}/progress`);
ws.onmessage = (event) => {
  const update = JSON.parse(event.data);
  updateProgressBar(update.progress);
  updateStatusText(update.message);
  
  if (update.status === 'completed') {
    loadResults(session.id);
  }
};

// 4. Start analysis
await startAnalysis(session.id);

// Progress updates stream automatically via WebSocket
// No polling needed!
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
