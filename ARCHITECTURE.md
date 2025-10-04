# Manufacturing QC System - Architecture Documentation

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture Diagram](#architecture-diagram)
3. [Backend Architecture](#backend-architecture)
4. [Frontend Architecture](#frontend-architecture)
5. [Data Flow](#data-flow)
6. [Technology Stack](#technology-stack)
7. [Security Considerations](#security-considerations)
8. [Scalability &amp; Performance](#scalability--performance)

---

## System Overview

The Manufacturing QC Cross-Check System is a full-stack web application designed to automate quality control validation for manufacturing documentation. The system follows a **client-server architecture** with clear separation of concerns:

- **Frontend**: React-based single-page application (SPA)
- **Backend**: FastAPI Python REST API with WebSocket support
- **Database**: SQLite for persistent storage
- **Communication**: HTTP/REST for API calls, WebSocket for real-time updates

### Key Architectural Principles

1. **Separation of Concerns**: Frontend handles UI/UX, backend handles business logic and data processing
2. **Stateless API**: Each request is self-contained (except WebSocket connections)
3. **Asynchronous Processing**: Long-running analysis tasks use async/await patterns
4. **Real-time Updates**: WebSocket streams provide live progress feedback
5. **Data Persistence**: All sessions, files, and results are stored for historical reference

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                            │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────────┐  │
│  │          React Frontend (Port 3000)                      │  │
│  ├──────────────────────────────────────────────────────────┤  │
│  │  • Session Management                                    │  │
│  │  • File Upload Interface                                 │  │
│  │  • Real-time Progress Monitor (WebSocket)                │  │
│  │  • Results Dashboard                                     │  │
│  └────────────┬─────────────────────────────┬───────────────┘  │
│               │ HTTP/REST                   │ WebSocket        │
└───────────────┼─────────────────────────────┼──────────────────┘
                │                             │
┌───────────────┼─────────────────────────────┼──────────────────┐
│               │    NGINX REVERSE PROXY      │                  │
│               │    (Docker Container)        │                  │
└───────────────┼─────────────────────────────┼──────────────────┘
                │                             │
┌───────────────▼─────────────────────────────▼──────────────────┐
│                      SERVER LAYER                               │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────────┐  │
│  │       FastAPI Backend (Port 8000)                        │  │
│  ├──────────────────────────────────────────────────────────┤  │
│  │                  API Routes                              │  │
│  │  ┌────────────┬────────────┬──────────┬────────────┐    │  │
│  │  │ Sessions   │ Files      │ Analysis │ Results    │    │  │
│  │  │ CRUD       │ Upload     │ Control  │ Retrieval  │    │  │
│  │  └────────────┴────────────┴──────────┴────────────┘    │  │
│  │                                                           │  │
│  │               WebSocket Manager                          │  │
│  │  ┌────────────────────────────────────────────────┐     │  │
│  │  │ Real-time Progress Broadcasting                │     │  │
│  │  │ Multi-client Connection Management             │     │  │
│  │  └────────────────────────────────────────────────┘     │  │
│  │                                                           │  │
│  │                Service Layer                             │  │
│  │  ┌────────────┬────────────┬────────────┬─────────┐     │  │
│  │  │ PDF Parser │ OCR Service│ Excel      │ Data    │     │  │
│  │  │            │            │ Parser     │ Normaliz│     │  │
│  │  └────────────┴────────────┴────────────┴─────────┘     │  │
│  │                                                           │  │
│  │             Validation Engine                            │  │
│  │  ┌─────────────────────────────────────────────────┐    │  │
│  │  │ 7-Check Validation Logic                        │    │  │
│  │  │ Priority-based Status Determination             │    │  │
│  │  └─────────────────────────────────────────────────┘    │  │
│  └──────────────────────────┬───────────────────────────────┘  │
│                             │                                  │
│  ┌──────────────────────────▼───────────────────────────────┐ │
│  │              Database Layer (SQLAlchemy ORM)             │ │
│  ├──────────────────────────────────────────────────────────┤ │
│  │  ┌──────────┬──────────────┬──────────────────────┐     │ │
│  │  │ Sessions │ Uploaded     │ Validation           │     │ │
│  │  │ Table    │ Files Table  │ Results Table        │     │ │
│  │  └──────────┴──────────────┴──────────────────────┘     │ │
│  └──────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                     STORAGE LAYER                               │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┬──────────────┬──────────────────────────┐   │
│  │ SQLite DB    │ Uploads Dir  │ Logs Directory           │   │
│  │ (./data/)    │ (./uploads/) │ (./logs/)                │   │
│  └──────────────┴──────────────┴──────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Backend Architecture

### Overview

The backend is built with **FastAPI** (Python 3.12) and follows a **layered architecture** pattern:

1. **API Layer**: HTTP endpoints and WebSocket connections
2. **Service Layer**: Business logic and data processing
3. **Data Layer**: Database operations and file storage

### Directory Structure

```
backend/
├── app/
│   ├── main.py                 # FastAPI application entry point
│   ├── config.py               # Configuration and settings
│   ├── database.py             # SQLAlchemy setup
│   ├── logging_config.py       # Logging configuration
│   │
│   ├── models/                 # SQLAlchemy ORM models
│   │   ├── __init__.py
│   │   ├── session.py          # Session model
│   │   ├── file.py             # UploadedFile model
│   │   └── validation.py       # ValidationResult model
│   │
│   ├── schemas/                # Pydantic schemas for validation
│   │   ├── __init__.py
│   │   ├── session.py          # Session request/response schemas
│   │   ├── file.py             # File upload schemas
│   │   └── validation.py       # Validation result schemas
│   │
│   ├── routers/                # API route handlers
│   │   ├── __init__.py
│   │   ├── sessions.py         # Session CRUD endpoints
│   │   ├── files.py            # File upload endpoints
│   │   └── analysis.py         # Analysis control and results
│   │
│   ├── services/               # Business logic services
│   │   ├── __init__.py
│   │   ├── pdf_parser.py       # Traveler PDF text extraction
│   │   ├── ocr_service.py      # Image OCR with Tesseract/OpenCV
│   │   ├── excel_parser.py     # Excel BOM parsing
│   │   ├── normalizer.py       # Data normalization
│   │   └── validator.py        # 7-check validation engine
│   │
│   └── websocket/              # WebSocket functionality
│       ├── __init__.py
│       └── manager.py          # Connection and broadcast management
│
├── uploads/                    # Uploaded file storage (volume)
├── data/                       # SQLite database (volume)
├── logs/                       # Application logs (volume)
├── Dockerfile                  # Docker build configuration
└── requirements.txt            # Python dependencies
```

### Backend Flow

#### **Step 1: Session Creation**

**Endpoint**: `POST /api/sessions`

**Process**:

1. Receive session creation request
2. Generate unique UUID for session
3. Create database record with status `PENDING`
4. Return session object to client

**Database**:

```sql
INSERT INTO sessions (id, created_at, status)
VALUES ('uuid', 'timestamp', 'PENDING');
```

**Features**:

- Automatic UUID generation
- Timestamp tracking (created_at, updated_at)
- Status tracking through lifecycle

**Limitations**:

- No user authentication (single-user system)
- No session expiration/cleanup (manual deletion required)

---

#### **Step 2: File Upload**

**Endpoint**: `POST /api/sessions/{session_id}/files`

**Process**:

1. Validate file type and size
2. Check upload limits (1 traveler, 1 image, 1-4 BOMs)
3. Save file to disk at `./uploads/{session_id}/{file_type}/`
4. Create database record with file metadata
5. Return file object with processing status `PENDING`

**File Storage Structure**:

```
uploads/
└── {session_id}/
    ├── traveler/
    │   └── SANITIZED_TRAVELER.pdf
    ├── image/
    │   └── SANITIZED_IMAGE.png
    └── bom/
        ├── As_Built_80751.xlsm
        └── As_Built_82334.xlsx
```

**Features**:

- Organized file storage by session and type
- File size validation (50 MB limit)
- Extension validation per file type
- Duplicate prevention (rejects re-upload of same type)

**Limitations**:

- Fixed file type limits (1 traveler, 1 image, max 4 BOMs)
- No virus scanning
- No file compression
- Files stored unencrypted

---

#### **Step 3: Analysis Trigger**

**Endpoint**: `POST /api/sessions/{session_id}/analyze`

**Process**:

1. Validate file requirements (1 traveler + 1 image + 1-4 BOMs)
2. Update session status to `PROCESSING`
3. Establish WebSocket connection for progress updates
4. Execute validation pipeline asynchronously
5. Broadcast progress via WebSocket

**Features**:

- Pre-flight validation of file completeness
- Asynchronous processing (non-blocking)
- Real-time progress broadcasting
- Automatic error handling and status updates

**Limitations**:

- Sequential processing (no parallel pipelines)
- No pause/resume capability
- No partial results on failure
- Memory-intensive for large images

---

#### **Step 4: PDF Parsing (Traveler)**

**Service**: `TravelerPDFParser`

**Process**:

1. Extract text from PDF using `pdfplumber`
2. Parse job number (5-digit pattern)
3. Extract part numbers with revisions (e.g., `PCA-1153-03 Rev F`)
4. Identify board serials (format: `#####-####`)
5. Extract unit serial (format: `INF-####`)
6. Save structured data to database

**Technology**:

- **pdfplumber**: PDF text extraction
- **Regular expressions**: Pattern matching

**Features**:

- Multi-page PDF support
- Pattern-based extraction (job numbers, part numbers, serials)
- Revision detection (e.g., "Rev F", "REV C")
- Fuzzy matching for OCR-corrupted PDFs

**Extraction Patterns**:

```python
JOB_NUMBER:     r'\b\d{5}\b'                    # 82334
PART_NUMBER:    r'PCA-\d{4}-\d{2} Rev [A-Z]'   # PCA-1153-03 Rev F
BOARD_SERIAL:   r'\b\d{5}-\d{4}\b'             # 80751-0053
UNIT_SERIAL:    r'INF-\d{4}'                   # INF-1619
```

**Limitations**:

- Text-based PDFs only (scanned PDFs require OCR preprocessing)
- Pattern-dependent (new formats need new regex)
- No table structure parsing
- Limited handling of multi-column layouts

---

#### **Step 5: Image OCR Processing**

**Service**: `ProductImageOCR` → `HardwareImageExtractor`

**Process**:

1. Load image and handle EXIF orientation
2. **Black Lid Detection**: Find dark rectangular region (bottom-left)
3. **Black Lid OCR**: Extract text with inverted preprocessing
4. **Full Image OCR**: Downscale and process entire image
5. **PCB Tile OCR**: Divide image into 3 regions (top-left, top-right, bottom-right)
6. **White Label Detection**: Use HSV color space to find white stickers
7. **Multi-Rotation OCR**: Try 4 rotations (0°, 90°, 180°, 270°) per label
8. **Multi-Strategy OCR**: Apply 3 preprocessing methods (OTSU, inverted, adaptive)
9. **Pattern Extraction**: Extract VGN serials, PCA parts, revisions
10. **Association**: Map revisions to their respective part numbers
11. Save structured data to database

**Technology Stack**:

- **Tesseract OCR**: Text recognition engine
- **OpenCV (cv2)**: Image preprocessing
- **subprocess**: Direct Tesseract invocation for control

**OCR Strategies** (per label):

- 4 rotations × 3 preprocessing methods × 3 PSM modes = **36 attempts per label**
- Best result selected based on: presence of keywords (PCA, VGN) and text length

**Image Preprocessing Techniques**:

1. **Grayscale conversion**: Simplify color complexity
2. **OTSU thresholding**: Automatic binary threshold
3. **Adaptive thresholding**: Local region-based threshold
4. **Morphological operations**: Noise removal, feature enhancement
5. **Sharpening**: Enhance edge definition
6. **Inversion**: Handle white-on-black text
7. **Scaling**: Upscale small labels for better recognition

**White Label Detection**:

```python
# HSV color space filtering
lower_white = [0, 0, 180]    # Low saturation, high value
upper_white = [180, 80, 255]
mask = cv2.inRange(hsv, lower_white, upper_white)

# Contour analysis for rectangular labels
# Filter by size, aspect ratio, position
```

**Context-Aware Extraction**:

- Revisions only extracted from text containing part numbers
- Prevents false positives from random "R" letters
- Part-revision association maintained per label

**Features**:

- Advanced white label detection (HSV-based)
- Multi-rotation OCR (handles sideways labels)
- Multi-strategy preprocessing (robust to lighting)
- Context-aware revision extraction
- VGN prefix auto-addition to board serials
- Flight status detection ("FLIGHT" vs "EDU - NOT FOR FLIGHT")

**Limitations**:

- Processing time: 20-40 seconds for typical PCB image
- Memory-intensive for high-resolution images (>20 MB)
- No GPU acceleration
- Struggles with:
  - Extremely small text (<6 pixels height)
  - Heavy reflections/glare
  - Curved/warped labels
  - Handwritten text
  - Non-English characters

---

#### **Step 6: Excel BOM Parsing**

**Service**: `ExcelBOMParser` → `BOMAggregator`

**Process**:

1. Load Excel file (.xlsx, .xlsm) using `pandas` + `openpyxl`
2. **Dynamic Header Detection**: Search for keywords ("Assembly", "Part", "Rev")
3. **Smart Column Mapping**: Identify columns by name, not position
4. **Part Number Extraction**: Extract PCA-, DRW-, SWC-, INF- prefixed parts
5. **Revision Extraction**: Extract revision codes from "Assy Rev" column
6. **Job Number Detection**: Find 5-digit job numbers in filename or cells
7. **Aggregation**: Combine data from multiple BOM files
8. Save structured data to database

**Technology**:

- **pandas**: DataFrame operations
- **openpyxl**: Excel file engine

**Dynamic Header Detection**:

```python
# Search rows 0-20 for header keywords
keywords = ['Assembly', 'Part', 'Rev', 'QTY']
for row_idx in range(20):
    if all(keyword in row for keyword in keywords):
        header_row = row_idx
        break
```

**Smart Column Mapping**:

```python
# Find columns by name, not fixed position
columns = {
    'part_number': find_column(['Assembly', 'Part Number', 'Part #']),
    'revision': find_column(['Assy Rev', 'Rev', 'Revision']),
    'quantity': find_column(['QTY', 'Quantity'])
}
```

**Part Number Extraction Patterns**:

```python
r'^(PCA|DRW|SWC|INF)-[A-Z0-9-]+$'  # Matches:
# PCA-1153-03
# DRW-1608-03
# SWC-400
# INF-1619
```

**Features**:

- Handles varying Excel formats (dynamic headers)
- Multi-BOM aggregation (combines up to 4 files)
- Job number detection from filename and cells
- Part number format flexibility
- Blank row/column handling

**Limitations**:

- Requires English column headers
- Limited to standard table layouts (no pivot tables)
- No macro execution (.xlsm macros ignored)
- Performance degrades with >1000 rows per file
- No validation of duplicate part numbers across BOMs

---

#### **Step 7: Data Normalization**

**Service**: `DataNormalizer`

**Process**:

1. Collect data from all sources (PDF, Image, Excel)
2. **Board Serial Normalization**: Add `VGN-` prefix if missing
3. **Unit Serial Normalization**: Add `INF-` prefix if missing
4. **Job Number Normalization**: Trim whitespace, validate format
5. **Part Number Normalization**: Uppercase, dash standardization
6. **Revision Normalization**: Extract letter from "REV F" → "F"
7. **Deduplication**: Remove duplicate entries across sources
8. Return normalized dataset for validation

**Normalization Rules**:

| Data Type    | Input Example      | Normalized Output  | Rule               |
| ------------ | ------------------ | ------------------ | ------------------ |
| Board Serial | `80751-0053`     | `VGN-80751-0053` | Add VGN- prefix    |
| Board Serial | `VGN-80751-0053` | `VGN-80751-0053` | Already normalized |
| Unit Serial  | `1619`           | `INF-1619`       | Add INF- prefix    |
| Unit Serial  | `INF-1619`       | `INF-1619`       | Already normalized |
| Job Number   | `82334`          | `82334`          | Trim whitespace    |
| Part Number  | `pca-1153-03`    | `PCA-1153-03`    | Uppercase          |
| Revision     | `REV F`          | `F`              | Extract letter     |
| Revision     | `Rev E2`         | `E2`             | Extract code       |

**Features**:

- Cross-source deduplication
- Format standardization
- Prefix addition (VGN-, INF-)
- Case normalization
- Whitespace handling

**Limitations**:

- Rules are hardcoded (not configurable)
- No fuzzy matching (exact format required)
- Assumes specific prefix patterns (VGN-, INF-)
- Cannot normalize unknown formats

---

#### **Step 8: Validation Engine (7 Checks)**

**Service**: `ValidationEngine`

**Process**: Execute 7 priority-ordered validation checks

**Check 1: Job Number**

- **Purpose**: Verify job number exists in at least one BOM
- **Data Sources**: Traveler PDF, Excel BOMs
- **Logic**:
  ```python
  if job_number in bom_job_numbers:
      status = PASS
  else:
      status = FAIL
  ```
- **Status**:
  - PASS: Job found in BOM(s)
  - FAIL: Job not found in any BOM

**Check 2: Part Number**

- **Purpose**: Ensure all parts from traveler/image exist in BOMs
- **Data Sources**: Traveler PDF, Image OCR, Excel BOMs
- **Logic**: For each unique part number:
  ```python
  if part_number in bom_part_numbers:
      status = PASS
  else:
      status = FAIL
  ```
- **Status**:
  - PASS: Part found in BOM(s)
  - FAIL: Part not found in any BOM
- **Multiple Results**: Creates one check result per part number

**Check 3: Revision**

- **Purpose**: Compare revision codes across sources
- **Data Sources**: Traveler PDF, Image OCR, Excel BOMs
- **Logic**: For each part with revision:
  ```python
  if image_revision == bom_revision:
      status = PASS
  elif image_revision in bom_revision or bom_revision in image_revision:
      status = WARNING  # Minor difference (e.g., "F" vs "F2")
  else:
      status = FAIL
  ```
- **Status**:
  - PASS: Exact match
  - WARNING: Partial match (e.g., "E" vs "E2")
  - FAIL: Complete mismatch
- **Multiple Results**: One per part number with revision

**Check 4: Board Serial**

- **Purpose**: Cross-check board serials between image and traveler
- **Data Sources**: Traveler PDF, Image OCR
- **Logic**: For each board serial:
  ```python
  normalized_image = normalize(image_serial)  # Add VGN- prefix
  normalized_traveler = normalize(traveler_serial)

  if normalized_image == normalized_traveler:
      status = PASS
  else:
      status = FAIL
  ```
- **Status**:
  - PASS: Serials match after normalization
  - FAIL: Serials don't match
- **Multiple Results**: One per board serial

**Check 5: Unit Serial**

- **Purpose**: Validate unit serial consistency
- **Data Sources**: Traveler PDF, Image OCR
- **Logic**:
  ```python
  normalized_image = normalize(image_unit_serial)  # Add INF- prefix
  normalized_traveler = normalize(traveler_unit_serial)

  if normalized_image == normalized_traveler:
      status = PASS
  else:
      status = FAIL
  ```
- **Status**:
  - PASS: Unit serials match
  - FAIL: Unit serials don't match

**Check 6: Flight Status**

- **Purpose**: Confirm hardware flight qualification
- **Data Sources**: Image OCR
- **Logic**:
  ```python
  if "FLIGHT" in image_text:
      status = PASS
  elif "EDU" in image_text or "NOT FOR FLIGHT" in image_text:
      status = INFO
  else:
      status = WARNING
  ```
- **Status**:
  - PASS: "FLIGHT" marking detected
  - INFO: "EDU - NOT FOR FLIGHT" marking detected
  - WARNING: No flight status found

**Check 7: File Completeness**

- **Purpose**: Verify all required files uploaded
- **Data Sources**: Session files
- **Logic**:
  ```python
  if traveler_count == 1 and image_count == 1 and bom_count >= 1:
      status = PASS
  else:
      status = FAIL
  ```
- **Status**:
  - PASS: All required files present
  - FAIL: Missing required files

**Overall Status Determination**:

```python
# Priority hierarchy: FAIL > WARNING > PASS > INFO
if any(check.status == FAIL):
    overall_status = FAIL
elif any(check.status == WARNING):
    overall_status = WARNING
elif all(check.status in [PASS, INFO]):
    overall_status = PASS
```

**Features**:

- Priority-ordered checks (most critical first)
- Granular results (multiple checks per type)
- Evidence preservation (all source data stored)
- Status hierarchy (FAIL overrides all)
- Real-time WebSocket broadcasting per check

**Limitations**:

- Fixed validation logic (not customizable)
- No weighting (all FAILs equal)
- No conditional checks (all 7 always run)
- No machine learning/fuzzy matching

---

#### **Step 9: Results Storage**

**Database Tables**:

**sessions**:

```sql
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    created_at DATETIME,
    updated_at DATETIME,
    status TEXT,  -- PENDING, PROCESSING, COMPLETED, FAILED
    overall_result TEXT  -- PASS, WARNING, FAIL
);
```

**uploaded_files**:

```sql
CREATE TABLE uploaded_files (
    id TEXT PRIMARY KEY,
    session_id TEXT,
    filename TEXT,
    file_type TEXT,  -- TRAVELER, IMAGE, BOM
    storage_path TEXT,
    file_size INTEGER,
    processing_status TEXT,
    uploaded_at DATETIME,
    processed_at DATETIME,
    extracted_data JSON,  -- Structured extraction results
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);
```

**validation_results**:

```sql
CREATE TABLE validation_results (
    id TEXT PRIMARY KEY,
    session_id TEXT,
    check_name TEXT,  -- Job Number, Part Number, etc.
    check_priority INTEGER,  -- 1-7
    status TEXT,  -- PASS, WARNING, FAIL, INFO
    message TEXT,
    expected_value TEXT,
    actual_value TEXT,
    evidence JSON,  -- Detailed evidence data
    created_at DATETIME,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);
```

**Features**:

- Full audit trail (all data preserved)
- JSON columns for flexible data storage
- Foreign key relationships for data integrity
- Timestamp tracking for analysis duration

**Limitations**:

- No automatic cleanup (sessions persist indefinitely)
- SQLite limitations:
  - No concurrent writes (single writer)
  - File-based (not ideal for high concurrency)
  - No built-in replication

---

#### **Step 10: WebSocket Broadcasting**

**Service**: `WebSocketManager`

**Process**:

1. Client connects via `ws://localhost:8000/api/ws/{session_id}/progress`
2. Manager stores connection in `active_connections` dict
3. During analysis, pipeline broadcasts updates:
   ```python
   await manager.broadcast(session_id, {
       "phase": "Image OCR",
       "message": "Processing white labels...",
       "progress": 45,
       "status": "processing"
   })
   ```
4. Manager sends message to all connected clients for that session
5. On completion, sends final status and closes connection

**Connection Management**:

```python
class WebSocketManager:
    active_connections: Dict[str, List[WebSocket]] = {}
  
    async def connect(session_id: str, websocket: WebSocket):
        # Add to connections
      
    async def disconnect(session_id: str, websocket: WebSocket):
        # Remove from connections
      
    async def broadcast(session_id: str, message: dict):
        # Send to all clients for this session
```

**Features**:

- Multi-client support (multiple browser tabs)
- Automatic reconnection handling
- Connection state tracking
- Graceful disconnection
- Session-scoped broadcasting

**Limitations**:

- In-memory connection storage (lost on restart)
- No message persistence (missed messages not recoverable)
- No authentication on WebSocket
- Single-server only (no distributed WebSocket)

---

### Backend Technology Stack

| Component        | Technology        | Purpose                       |
| ---------------- | ----------------- | ----------------------------- |
| Web Framework    | FastAPI           | Async REST API and WebSocket  |
| ORM              | SQLAlchemy        | Database abstraction          |
| Database         | SQLite            | Persistent storage            |
| PDF Parsing      | pdfplumber        | Text extraction from PDFs     |
| OCR Engine       | Tesseract         | Image text recognition        |
| Image Processing | OpenCV (cv2)      | Preprocessing and enhancement |
| Excel Parsing    | pandas + openpyxl | Excel file reading            |
| Data Validation  | Pydantic          | Request/response schemas      |
| Async Tasks      | asyncio           | Non-blocking operations       |
| Logging          | Python logging    | Application and error logs    |

---

## Frontend Architecture

### Overview

The frontend is a **React 18 single-page application (SPA)** built with JavaScript and Material-UI. It follows a **component-based architecture** with clear separation between UI, business logic, and API communication.

### Directory Structure

```
frontend/
├── public/                     # Static assets
│   └── vite.svg
│
├── src/
│   ├── main.jsx                # React entry point
│   ├── App.jsx                 # Main app component
│   │
│   ├── components/             # React components
│   │   ├── SessionManager.jsx  # Session creation and selection
│   │   ├── FileUploader.jsx    # File upload interface
│   │   ├── ProgressMonitor.jsx # Real-time analysis progress
│   │   └── ValidationResults.jsx # Results display
│   │
│   ├── services/               # API communication layer
│   │   └── api.js              # HTTP and WebSocket helpers
│   │
│   ├── hooks/                  # Custom React hooks
│   │   └── useWebSocket.js     # WebSocket connection hook
│   │
│   ├── theme/                  # Material-UI theming
│   │   └── theme.js            # Color palette and typography
│   │
│   └── index.css               # Global styles
│
├── nginx.conf                  # Nginx configuration for production
├── Dockerfile                  # Multi-stage Docker build
├── package.json                # NPM dependencies
└── vite.config.js              # Vite build configuration
```

### Frontend Flow

#### **Step 1: Application Initialization**

**Component**: `main.jsx` → `App.jsx`

**Process**:

1. React renders `App` component
2. Material-UI theme provider wraps application
3. Initial state initialized:
   ```javascript
   const [currentSession, setCurrentSession] = useState(null);
   const [isAnalyzing, setIsAnalyzing] = useState(false);
   const [analysisCompleted, setAnalysisCompleted] = useState(false);
   ```
4. App structure rendered:
   - App Bar (header)
   - Container (main content)
   - Footer

**Features**:

- Material-UI theme customization
- Responsive layout (mobile-friendly)
- Global state management via React hooks
- Component-based structure

**Limitations**:

- No state management library (Redux, Zustand)
- No routing library (React Router) - single page only
- No internationalization (English only)

---

#### **Step 2: Session Management**

**Component**: `SessionManager.jsx`

**Process**:

1. On mount, fetch recent sessions:
   ```javascript
   useEffect(() => {
     fetchSessions();
   }, []);
   ```
2. Display session list with status badges
3. User actions:
   - **New Session**: Click "New Session" button
     ```javascript
     const response = await sessionAPI.create();
     setCurrentSession(response);
     ```
   - **Select Existing**: Click on session in list
     ```javascript
     const response = await sessionAPI.get(sessionId);
     setCurrentSession(response);
     ```

**UI Elements**:

- "New Session" button
- Recent sessions list (scrollable)
- Session ID (first 8 chars displayed)
- Status chip (PENDING, PROCESSING, COMPLETED)
- Overall result chip (PASS, WARNING, FAIL)
- Created timestamp

**State Management**:

```javascript
const [sessions, setSessions] = useState([]);
const [loading, setLoading] = useState(true);
const [creating, setCreating] = useState(false);
const [error, setError] = useState(null);
```

**Features**:

- Session history display
- Auto-refresh on session change
- Visual status indicators
- Error handling with user feedback

**Limitations**:

- No pagination (shows all sessions)
- No search/filter capability
- No bulk operations (delete multiple)
- No session metadata editing

---

#### **Step 3: File Upload**

**Component**: `FileUploader.jsx`

**Process**:

1. Component renders three upload areas:
   - Traveler PDF (1 required)
   - Product Image (1 required)
   - BOM Excel files (1-4 required)
2. User uploads files via:
   - **Drag & Drop**: Drop file onto upload area
   - **Click**: Click area to open file picker
3. On file selection:
   ```javascript
   const formData = new FormData();
   formData.append('file', file);
   formData.append('file_type', type);
   await fileAPI.upload(sessionId, formData);
   ```
4. After upload, fetch updated file list:
   ```javascript
   const files = await fileAPI.list(sessionId);
   ```
5. Display file counts and enable "Analyze" button when ready

**Upload Validation**:

```javascript
// Client-side validation before upload
const validExtensions = {
  traveler: ['.pdf'],
  image: ['.jpg', '.jpeg', '.png'],
  bom: ['.xlsx', '.xlsm']
};

if (!validExtensions[type].includes(fileExtension)) {
  alert('Invalid file type');
  return;
}
```

**File Count Display**:

```javascript
const requirements = {
  traveler: { uploaded: travelerCount, required: 1 },
  image: { uploaded: imageCount, required: 1 },
  bom: { uploaded: bomCount, required: '1-4' }
};
```

**Analyze Button Logic**:

```javascript
const canStartAnalysis = 
  travelerCount === 1 && 
  imageCount === 1 && 
  bomCount >= 1 && 
  bomCount <= 4;
```

**Features**:

- Drag-and-drop interface
- Real-time file count updates
- Visual upload progress (via MUI components)
- File type validation
- Requirements display (✓ or ✗)
- Smart button enabling

**Limitations**:

- No file preview before upload
- No chunked upload (entire file in one request)
- No upload resume on failure
- No client-side virus scanning
- No image compression before upload
- File size limit enforced server-side only

---

#### **Step 4: Analysis Trigger**

**Component**: `FileUploader.jsx` (Analyze button)

**Process**:

1. User clicks "Analyze" button (enabled when requirements met)
2. Trigger analysis:
   ```javascript
   const handleAnalyze = async () => {
     await analysisAPI.start(sessionId);
     onAnalysisStart();  // Notify parent
   };
   ```
3. Parent `App.jsx` updates state:
   ```javascript
   setIsAnalyzing(true);
   setAnalysisCompleted(false);
   ```
4. UI transitions to progress monitoring view

**Features**:

- One-click analysis trigger
- Automatic UI transition
- Error handling with user feedback
- Button disabled during analysis

**Limitations**:

- No confirmation dialog (accidental clicks)
- No analysis options (e.g., "skip OCR")
- Cannot cancel once started

---

#### **Step 5: Real-Time Progress Monitoring**

**Component**: `ProgressMonitor.jsx` + Custom Hook: `useWebSocket.js`

**Process**:

1. Component mounts and connects to WebSocket:
   ```javascript
   const { progress, status, message, phase, details, isConnected } = 
     useWebSocket(sessionId);
   ```
2. Custom hook manages WebSocket lifecycle:
   ```javascript
   useEffect(() => {
     const ws = new WebSocket(`ws://localhost:8000/api/ws/${sessionId}/progress`);

     ws.onopen = () => setIsConnected(true);

     ws.onmessage = (event) => {
       const data = JSON.parse(event.data);
       setProgress(data.progress);
       setMessage(data.message);
       setPhase(data.phase);
       setDetails(data.details);
     };

     ws.onerror = () => setIsConnected(false);
     ws.onclose = () => setIsConnected(false);

     return () => ws.close();  // Cleanup
   }, [sessionId]);
   ```
3. Component displays:
   - Overall progress bar (0-100%)
   - Current phase
   - Status message
   - Pipeline phases table (with checkmarks)
   - Live validation checks (as they arrive)

**Live Validation Checks Display**:

```javascript
// Capture check results from WebSocket details
useEffect(() => {
  if (details?.check_name && details?.check_status) {
    const checkResult = {
      check_number: details.check_number,
      check_name: details.check_name,
      status: details.check_status,
      message: details.check_message,
      expected_value: details.expected_value,
      actual_value: details.actual_value,
      timestamp: new Date()
    };
  
    // Accumulate checks (allow multiple per check_number)
    setLiveCheckResults(prev => {
      const exists = prev.find(c => 
        c.check_number === checkResult.check_number &&
        c.expected_value === checkResult.expected_value &&
        c.message === checkResult.message
      );
    
      if (exists) {
        return prev.map(c => 
          c.check_number === checkResult.check_number ? checkResult : c
        );
      }
    
      return [...prev, checkResult];
    });
  }
}, [details]);
```

**UI Sections**:

1. **Progress Card**: Overall progress and status
2. **Pipeline Phases Table**: Shows 9 processing steps
3. **Live Validation Checks**: Real-time check results with status icons
4. **Status Messages**: Detailed messages from backend

**Features**:

- Real-time WebSocket updates
- Live validation check display
- Sub-check visualization (indentation)
- Identifier chips (job number, part numbers, serials)
- Progress percentage display
- Pipeline phase tracking
- Automatic reconnection on disconnect
- Check persistence after completion

**Limitations**:

- No pause/resume UI
- No manual refresh capability
- No error retry mechanism
- WebSocket messages not persisted (page refresh loses progress)
- No offline support

---

#### **Step 6: Results Display**

**Component**: `ValidationResults.jsx`

**Process**:

1. Component mounts when analysis completes
2. Fetch results from API:
   ```javascript
   useEffect(() => {
     if (sessionId) {
       const response = await analysisAPI.getResults(sessionId);
       setResults(response);
     }
   }, [sessionId]);
   ```
3. Parse results structure:
   ```javascript
   const { results: checks, overall_status } = response;
   ```
4. Display UI:
   - Overall status alert (PASS/WARNING/FAIL)
   - Summary counts (X Passed, Y Warnings, Z Failed)
   - Expandable accordions for each check
   - Evidence tables with expected vs actual

**Accordion Structure**:

```javascript
{checks.map(check => (
  <Accordion key={check.id}>
    <AccordionSummary>
      {/* Check name, status chip, message */}
    </AccordionSummary>
    <AccordionDetails>
      {/* Evidence table with key-value pairs */}
    </AccordionDetails>
  </Accordion>
))}
```

**Status Summary Calculation**:

```javascript
const counts = {
  passed: checks.filter(c => c.status?.toLowerCase() === 'pass').length,
  warnings: checks.filter(c => c.status?.toLowerCase() === 'warning').length,
  failed: checks.filter(c => c.status?.toLowerCase() === 'fail').length,
  info: checks.filter(c => c.status?.toLowerCase() === 'info').length
};
```

**Features**:

- Overall status badge with icon
- Summary counts with color-coded chips
- Expandable check details
- Evidence tables (key-value display)
- Array and object rendering in evidence
- Color-coded accordions by status
- Status symbols (✓, ✗, ⚠, ℹ)

**Limitations**:

- No CSV/PDF export
- No printable view
- No comparison with previous sessions
- No filtering/sorting of checks
- Cannot hide/show specific checks

---

### Frontend Technology Stack

| Component        | Technology                        | Purpose                                |
| ---------------- | --------------------------------- | -------------------------------------- |
| UI Library       | React 18                          | Component-based UI                     |
| Language         | JavaScript (ES6+)                 | Application logic                      |
| UI Framework     | Material-UI (MUI)                 | Professional components                |
| Build Tool       | Vite                              | Fast development and production builds |
| HTTP Client      | Fetch API                         | REST API communication                 |
| WebSocket Client | Native WebSocket                  | Real-time updates                      |
| State Management | React Hooks (useState, useEffect) | Component state                        |
| Web Server       | Nginx                             | Production static file serving         |
| Package Manager  | Yarn                              | Dependency management                  |

---

## Data Flow

### Complete End-to-End Flow

```
1. USER ACTION: Create Session
   ↓
   Frontend: POST /api/sessions
   ↓
   Backend: Create session in database
   ↓
   Backend: Return session object (status: PENDING)
   ↓
   Frontend: Display session info

2. USER ACTION: Upload Files (3 files)
   ↓
   Frontend: POST /api/sessions/{id}/files (traveler)
   Frontend: POST /api/sessions/{id}/files (image)
   Frontend: POST /api/sessions/{id}/files (bom)
   ↓
   Backend: Validate each file
   Backend: Save to ./uploads/{session_id}/{type}/
   Backend: Create file records in database
   ↓
   Backend: Return file objects
   ↓
   Frontend: Update file counts, enable "Analyze" button

3. USER ACTION: Click "Analyze"
   ↓
   Frontend: POST /api/sessions/{id}/analyze
   ↓
   Backend: Validate file requirements
   Backend: Update session status → PROCESSING
   Backend: Start async validation pipeline
   ↓
   Backend: Return 202 Accepted
   ↓
   Frontend: Connect WebSocket
   Frontend: Display progress monitor

4. BACKEND PROCESSING (Async):
   ↓
   Step 1: Parse PDF
   ├─ Extract job number, part numbers, serials
   └─ Broadcast progress: 10%
   ↓
   Step 2: OCR Image
   ├─ Detect white labels
   ├─ Multi-rotation OCR
   ├─ Extract VGN serials, PCA parts, revisions
   └─ Broadcast progress: 20-50%
   ↓
   Step 3: Parse Excel BOMs
   ├─ Dynamic header detection
   ├─ Extract part numbers, revisions
   └─ Broadcast progress: 60%
   ↓
   Step 4: Normalize Data
   ├─ Add VGN-, INF- prefixes
   ├─ Standardize formats
   └─ Broadcast progress: 70%
   ↓
   Step 5: Run 7 Validation Checks
   ├─ Check 1: Job Number → Broadcast result
   ├─ Check 2: Part Numbers → Broadcast each result
   ├─ Check 3: Revisions → Broadcast each result
   ├─ Check 4: Board Serials → Broadcast each result
   ├─ Check 5: Unit Serial → Broadcast result
   ├─ Check 6: Flight Status → Broadcast result
   └─ Check 7: File Completeness → Broadcast result
   ↓
   Step 6: Calculate Overall Status
   ├─ Determine PASS/WARNING/FAIL
   └─ Broadcast progress: 100%, status: completed
   ↓
   Step 7: Save Results to Database
   ├─ Update session.overall_result
   ├─ Update session.status → COMPLETED
   └─ Save all check results

5. FRONTEND RECEIVES COMPLETION:
   ↓
   WebSocket: status = "completed"
   ↓
   Frontend: Update UI
   ├─ Show "Analysis Complete"
   ├─ Display live check results (persisted)
   └─ Show "Step 2: Validation Results"
   ↓
   Frontend: GET /api/sessions/{id}/results
   ↓
   Backend: Fetch results from database
   ↓
   Backend: Return results JSON
   ↓
   Frontend: Render detailed accordions

6. USER ACTION: View Check Details
   ↓
   Frontend: Expand accordion
   ↓
   Frontend: Display evidence table
```

---

## Security Considerations

### Current Security Posture

**Implemented**:

- Input validation (file types, sizes)
- SQL injection prevention (SQLAlchemy ORM)
- Path traversal prevention (UUID-based file storage)
- CORS configuration (configurable)

**Not Implemented (Single-User System)**:

- Authentication/authorization
- API rate limiting
- Session encryption
- File virus scanning
- HTTPS enforcement
- XSS protection headers
- CSRF tokens

### Recommendations for Production

1. **Add Authentication**: JWT or API key-based auth
2. **Enable HTTPS**: TLS certificates for encrypted communication
3. **Implement Rate Limiting**: Prevent abuse
4. **Add Virus Scanning**: ClamAV integration for uploaded files
5. **Session Expiration**: Automatic cleanup of old sessions
6. **Input Sanitization**: Enhanced validation for all inputs
7. **Audit Logging**: Track all user actions

---

## Scalability & Performance

### Current Limitations

**Backend**:

- Single-threaded OCR processing (20-40s per image)
- SQLite limited to single writer
- No caching layer
- Memory-intensive image processing
- No distributed processing

**Frontend**:

- No lazy loading of session list
- All validation checks loaded at once
- No image optimization before upload

### Scaling Recommendations

**For 10-50 concurrent users**:

1. **PostgreSQL**: Replace SQLite for concurrent writes
2. **Redis Caching**: Cache session data, results
3. **Celery Workers**: Distribute OCR processing
4. **Load Balancer**: Nginx for multiple backend instances
5. **CDN**: Serve frontend static files

**For 100+ concurrent users**:
6. **Kubernetes**: Container orchestration
7. **Message Queue**: RabbitMQ for job distribution
8. **Object Storage**: S3 for uploaded files
9. **GPU Acceleration**: CUDA-enabled Tesseract
10. **Microservices**: Separate PDF, OCR, Excel services

---

## Summary

The Manufacturing QC System is a **well-architected full-stack application** with:

✅ **Clear separation** between frontend and backend
✅ **Modular service layer** for data processing
✅ **Real-time communication** via WebSockets
✅ **Comprehensive validation** with 7-check engine
✅ **Persistent storage** with full audit trail
✅ **Production-ready** Docker deployment

**Suitable for**: Internal manufacturing QC teams (1-20 concurrent users)

**Future enhancements needed for**: Multi-tenant SaaS, high-concurrency environments

---

**End of Architecture Documentation**
