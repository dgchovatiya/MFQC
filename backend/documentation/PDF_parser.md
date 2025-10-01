# PDF Parser Service - Complete Guide

## 📋 **Table of Contents**

1. [Architecture Overview](#architecture-overview)
2. [PDF Parsing Logic](#pdf-parsing-logic)
3. [Completeness Score System](#completeness-score-system)
4. [Testing Guide](#testing-guide)
5. [Troubleshooting](#troubleshooting)

---

## 🏗️ **Architecture Overview**

### **Corrected Processing Flow**

```
1. USER UPLOADS FILES → Files saved to disk (FAST)
   ├── Traveler PDF → status: "pending", extracted_data: null
   ├── Product Image → status: "pending", extracted_data: null
   └── BOM Excel files → status: "pending", extracted_data: null
   
2. USER CLICKS "START ANALYSIS" → Analysis endpoint triggered
   
3. VALIDATION PIPELINE RUNS (Background):
   ├── Parse PDF Traveler → Extract manufacturing data

4. RESULTS AVAILABLE → User views extracted data and validation
```

### **Key Architecture Principles**

| Aspect                    | Upload Endpoint         | Analysis Endpoint                   |
| ------------------------- | ----------------------- | ----------------------------------- |
| **Purpose**         | Save files to disk ONLY | Process ALL files in pipeline       |
| **Speed**           | < 1 second (file I/O)   | 2-5 seconds (background)            |
| **Status**          | Always `"pending"`    | `"processing"` → `"completed"` |
| **Data**            | Always `null`         | Extracted and stored                |
| **User Experience** | Fast, responsive        | Non-blocking, trackable             |

---

## 🔍 **PDF Parsing Logic**

### **Overview**

The PDF parser (`backend/app/services/pdf_parser.py`) extracts critical manufacturing data from Traveler documents using a multi-method approach with intelligent fallbacks.

### **What Gets Extracted**

#### **1. Job Numbers** (Critical - 1.0 point)

**Patterns Detected**:

- `"Job Number: 80641"`
- `"Work Order: 12345"`
- `"Job: 80641"`
- Standalone 5-digit numbers in headers

**Validation**:

- Must be exactly 5 digits
- Format: `^\d{5}$`
- Example: `80641` ✅, `8064` ❌

**Code Location**: Lines 220-243

---

#### **2. Work Instructions** (Critical - 1.0 point)

**Patterns Detected**:

- `"DRW-1234-01"`
- `"Work Instruction: DRW-XXXX-YY"`
- `"Drawing: DRW-1234-01"`

**Validation**:

- Format: `DRW-XXXX-YY` (case-insensitive)
- Regex: `^DRW-\d{4}-\d{2}$`
- Example: `DRW-1608-03` ✅, `DRW-123-4` ❌

**Code Location**: Lines 245-269

---

#### **3. Unit Serials** (Moderate - 0.5 points)

**Patterns Detected**:

- From Seq 20 sections: `"Unit Serial: 1619"`
- Standalone 4-digit codes near "unit" keyword
- Accepts both `INF-1619` and `1619` formats

**Validation**:

- Format: `INF-XXXX` or `XXXX` (4 digits)
- Regex: `^(INF-?)?\d{4}$`
- Example: `INF-1619` ✅, `1619` ✅ (warns about missing prefix)

**Normalization **:

- `1619` → `INF-1619` (prefix added automatically)

**Code Location**: Lines 271-330

---

#### **4. Board Serials** (Moderate - 0.5 points)

**Patterns Detected**:

- From Seq 20 sections: `"Board Serial: 12345-6789"`
- Accepts both `VGN-12345-6789` and `12345-6789` formats
- Multiple serials supported per PDF

**Validation**:

- Format: `VGN-XXXXX-XXXX` or `XXXXX-XXXX`
- Regex: `^(VGN-?)?\d{5}-?\d{4}$`
- Example: `VGN-12345-6789` ✅, `12345-6789` ✅ (warns about missing prefix)

**Normalization**:

- `12345-6789` → `VGN-12345-6789` (prefix added automatically)

**Code Location**: Lines 332-408

---

#### **5. Part Numbers with Revisions** (Nice-to-have - 0.3 points)

**Patterns Detected**:

- `"PCA-1234-05 Rev F2"`
- `"Part Number: PCA-1234-05 Rev F"`
- `"P/N: PCA-1234-05 F2"`

**Extraction**:

- Part Number: `PCA-1234-05`
- Revision: `F2` (normalized to uppercase, "Rev" prefix removed)

**Validation**:

- Part format: `^[A-Z]+-\d+(-\d+)*$`
- Example: `PCA-1234-05` ✅, `PCA-123` ✅, `pca-1234` ❌

**Code Location**: Lines 410-474

---

### **Detection Methods (Multi-Layer Fallback)**

The parser uses a sophisticated 3-layer detection strategy:

#### **Layer 1: Table Extraction** (Primary - Most Reliable)

```python
# Extract all tables from PDF
tables = page.extract_tables()

# Search for "Seq 20" in table cells
for table in tables:
    for row in table:
        if "seq 20" in str(row).lower():
            # Extract serials from this table
```

**Advantages**:

- ✅ Structured data extraction
- ✅ Highest accuracy for standard Traveler formats
- ✅ Preserves row/column relationships

**Code Location**: Lines 476-533

---

#### **Layer 2: Text Pattern Matching** (Secondary - Regex-Based)

```python
# Extract raw text from PDF
text = page.extract_text()

# Use regex to find Seq 20 sections
seq_20_match = re.search(r'seq\s*20.*?(?:seq\s*\d+|$)', text, re.IGNORECASE | re.DOTALL)

# Extract serials from matched section
```

**Advantages**:

- ✅ Works with non-tabular PDFs
- ✅ Flexible pattern matching
- ✅ Handles variations in formatting

**Code Location**: Lines 535-592

---

#### **Layer 3: General Pattern Search** (Fallback - Broad Matching)

```python
# Search entire document for serial patterns
unit_serial_matches = re.findall(r'(?:unit|serial).*?(\d{4})', text, re.IGNORECASE)
board_serial_matches = re.findall(r'(?:board|serial).*?(\d{5}-\d{4})', text, re.IGNORECASE)
```

**Advantages**:

- ✅ Catches edge cases
- ✅ Works with non-standard formats
- ✅ Ensures maximum data extraction

**Code Location**: Lines 594-650

---

### **Processing Pipeline**

```
1. OPEN PDF
   ├── Check file exists
   ├── Validate PDF format
   └── Handle corrupted/encrypted files
   
2. EXTRACT TEXT & TABLES
   ├── Extract from all pages
   ├── Count characters per page
   └── Store page metadata
   
3. FIND SEQ 20 SECTION
   ├── Method 1: Search in tables
   ├── Method 2: Search in text
   └── Method 3: Pattern fallback
   
4. EXTRACT MANUFACTURING DATA
   ├── Job number (5-digit pattern)
   ├── Work instruction (DRW-XXXX-YY)
   ├── Unit serial (from Seq 20)
   ├── Board serials (from Seq 20, multiple)
   └── Part numbers with revisions
   
5. VALIDATE EXTRACTED DATA
   ├── Format validation (regex patterns)
   ├── Completeness scoring (0-100%)
   ├── Generate warnings (missing prefixes)
   └── Generate errors (invalid formats)
   
6. RETURN STRUCTURED RESULT
   └── JSON with all data + metadata
```

---

## 📊 **Completeness Score System**

### **Overview**

The completeness score is a **normalized 0-100% metric** that measures how much critical manufacturing data was successfully extracted from the PDF.

**Purpose**: Quickly assess if the PDF contains enough information for validation.

---

### **Scoring Algorithm**

#### **Weighted Factors**:

```
Factor                  Points    Priority
──────────────────────────────────────────────
Job Number              1.0       Critical
Work Instruction        1.0       Critical
Unit Serial             0.5       Moderate
Board Serials           0.5       Moderate
Part Numbers            0.3       Nice-to-have
Seq 20 Found            0.2       Structural
Tables Extracted        0.1       Structural
Text Extracted          0.1       Basic
──────────────────────────────────────────────
MAXIMUM TOTAL:          3.7 points
```

#### **Calculation**:

```python
# Step 1: Add up all earned points
your_points = sum([
    1.0 if job_number else 0.0,
    1.0 if work_instruction else 0.0,
    0.5 if unit_serial else 0.0,
    0.5 if board_serials else 0.0,
    0.3 if part_numbers else 0.0,
    0.2 if seq_20_found else 0.0,
    0.1 if tables else 0.0,
    0.1 if text else 0.0
])

# Step 2: Normalize to 0-100% scale
MAX_POSSIBLE_SCORE = 3.7
completeness_score = (your_points / MAX_POSSIBLE_SCORE) * 100

# Example: All data found
# 3.7 / 3.7 = 1.0 = 100% ✅
```

**Code Location**: Lines 699-714

---

### **Score Examples**

#### **Perfect Extraction (100%)**:

```
✅ Job Number: 80641               (+1.0)
✅ Work Instruction: DRW-1234-01   (+1.0)
✅ Unit Serial: INF-1619           (+0.5)
✅ Board Serials: VGN-12345-6789   (+0.5)
✅ Part Numbers: PCA-1234-05 Rev F2 (+0.3)
✅ Seq 20 Found: Yes               (+0.2)
✅ Tables: 3 tables                (+0.1)
✅ Text: 2000 chars                (+0.1)
────────────────────────────────────────
Total: 3.7 / 3.7 = 100% ✅
```

---

#### **Excellent Extraction (95%)**:

```
✅ Job Number: 80641               (+1.0)
✅ Work Instruction: DRW-1234-01   (+1.0)
✅ Unit Serial: 1619               (+0.5)
✅ Board Serials: 12345-6789       (+0.5)
✅ Part Numbers: PCA-1234-05 Rev F2 (+0.3)
❌ Seq 20 Found: No                (+0.0) -0.2
✅ Tables: 2 tables                (+0.1)
✅ Text: 1500 chars                (+0.1)
────────────────────────────────────────
Total: 3.5 / 3.7 = 94.6% ✅

⚠️ Warnings:
- Unit serial missing INF- prefix: '1619'
- Board serial missing VGN- prefix: '12345-6789'
```

---

#### **Good Extraction (73%)**:

```
✅ Job Number: 80641               (+1.0)
✅ Work Instruction: DRW-1234-01   (+1.0)
✅ Unit Serial: 1619               (+0.5)
❌ Board Serials: Not found        (+0.0) -0.5
❌ Part Numbers: Not found         (+0.0) -0.3
❌ Seq 20 Found: No                (+0.0) -0.2
✅ Tables: 1 table                 (+0.1)
✅ Text: 500 chars                 (+0.1)
────────────────────────────────────────
Total: 2.7 / 3.7 = 73.0% ✅
```

---

#### **Fair Extraction (59%)**:

```
✅ Job Number: 80641               (+1.0)
✅ Work Instruction: DRW-1234-01   (+1.0)
❌ Unit Serial: Not found          (+0.0) -0.5
❌ Board Serials: Not found        (+0.0) -0.5
❌ Part Numbers: Not found         (+0.0) -0.3
❌ Seq 20 Found: No                (+0.0) -0.2
✅ Tables: 1 table                 (+0.1)
✅ Text: 500 chars                 (+0.1)
────────────────────────────────────────
Total: 2.2 / 3.7 = 59.5% ⚠️
```

---

### **Score Interpretation**

| Score Range         | Status       | Meaning                         | Action Required      |
| ------------------- | ------------ | ------------------------------- | -------------------- |
| **90-100%**   | ✅ Excellent | All critical data extracted     | Ready for validation |
| **70-89%**    | ✅ Good      | Most critical data present      | Can proceed          |
| **50-69%**    | ⚠️ Fair    | Basic data, missing some fields | May need review      |
| **Below 50%** | ❌ Poor      | Critical data missing           | Re-upload required   |

---

### **Why Normalized Scoring?**

**Problem with Raw Scoring**:

```python
# Old approach (CONFUSING)
score = sum(factors) / 8
# Max: 3.7 / 8 = 0.4625 = 46.25% ❌
# User sees: "46% complete" (but it's actually perfect!)
```

**Solution with Normalized Scoring**:

```python
# New approach (CLEAR)
score = sum(factors) / 3.7
# Max: 3.7 / 3.7 = 1.0 = 100% ✅
# User sees: "100% complete" (actually perfect!)
```

**Benefits**:

- ✅ Intuitive (100% = perfect, as expected)
- ✅ Matches industry standards (like grade normalization)
- ✅ Still mathematically accurate (proportional weighting)
- ✅ Self-explanatory (no PhD in statistics required)

---

## 🧪 **Testing Guide**

### **1. Start the Server**

```bash
cd backend
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Mac/Linux
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

**Server URLs**:

- **API**: http://127.0.0.1:8000
- **Swagger UI**: http://127.0.0.1:8000/docs
- **Logs**: `backend/logs/app.log`

---

### **2. Interactive Testing (Swagger UI)**

#### **Step 1: Create Session**

1. Open http://127.0.0.1:8000/docs
2. Expand `POST /api/sessions/`
3. Click "Try it out" → "Execute"
4. **Copy the session ID**

#### **Step 2: Upload Traveler PDF**

1. Expand `POST /api/sessions/{session_id}/files`
2. Paste session ID
3. Select PDF file
4. Set `file_type` to `traveler`
5. Click "Execute"

**Expected Response**:

```json
{
  "processing_status": "pending",  // NOT processed yet!
  "extracted_data": null           // NO data yet!
}
```

#### **Step 3: Upload Image & BOM**

- Upload with `file_type` = `image` (1 file)
- Upload with `file_type` = `bom` (1-4 files)

#### **Step 4: Start Analysis**

1. Expand `POST /api/sessions/{session_id}/analyze`
2. Paste session ID
3. Click "Execute"
4. **Check `backend/logs/app.log` for processing logs**

**Expected Log Output**:

```
[2024-10-01 14:30:17] INFO - Processing Traveler PDF: sample.pdf
[2024-10-01 14:30:17] INFO - Successfully processed sample.pdf
[2024-10-01 14:30:17] INFO - Extracted Data Summary:
[2024-10-01 14:30:17] INFO -   - Job Number: 80641
[2024-10-01 14:30:17] INFO -   - Work Instruction: DRW-1234-01
[2024-10-01 14:30:17] INFO -   - Unit Serial: 1619
[2024-10-01 14:30:17] INFO -   - Board Serials: 1 found
[2024-10-01 14:30:17] INFO -   - Part Numbers: 1 found
[2024-10-01 14:30:17] INFO -   - Seq 20 Found: True
[2024-10-01 14:30:17] INFO -   - Completeness Score: 94.6%
```

#### **Step 5: Check Results**

1. Expand `GET /api/sessions/{session_id}/files`
2. Paste session ID
3. Click "Execute"

**Expected Response**:

```json
[{
  "filename": "sample.pdf",
  "file_type": "traveler",
  "processing_status": "completed",  // NOW processed!
  "extracted_data": {
    "parsing_status": "success",
    "job_number": "80641",
    "work_instruction": "DRW-1234-01",
    "unit_serial": "1619",
    "board_serials": ["12345-6789"],
    "part_numbers": [
      {"part_number": "PCA-1234-05", "revision": "F2"}
    ],
    "seq_20_data": {"found": true, "method": "table_extraction"},
    "validation": {
      "completeness_score": 0.946,  // 94.6%
      "validation_warnings": [
        "Unit serial missing INF- prefix: '1619'",
        "Board serial missing VGN- prefix: '12345-6789'"
      ]
    }
  }
}]
```

---

### **3. Sample Test PDF Content**

Create `test_traveler.pdf` with this content:

```
TRAVELER WORK INSTRUCTION

Job Number: 80641
Work Instruction: DRW-1234-01

SEQ 20 - ASSEMBLY VERIFICATION
Unit Serial: 1619
Board Serial: 12345-6789
Board Serial: 98765-4321
Part Number: PCA-1234-05 Rev F2
Part Number: PCA-5678-02 Rev G1

Flight Status: FLIGHT
Assembly Date: 2024-10-01
Inspector: QC Team
```

**Expected Results**:

- Job Number: `80641` ✅
- Work Instruction: `DRW-1234-01` ✅
- Unit Serial: `1619` ✅ (warning: missing INF- prefix)
- Board Serials: `12345-6789`, `98765-4321` ✅ (warnings: missing VGN- prefixes)
- Part Numbers: 2 found ✅
- Completeness Score: **100%** ✅

---

## 🐛 **Troubleshooting**

### **Issue 1: Upload shows extracted_data**

**Symptom**: File upload response contains `extracted_data` with parsed information.

**Cause**: Processing happening during upload (incorrect flow).

**Solution**:

1. Check `backend/app/api/files.py` line 12
2. Should NOT import `pdf_parser_service`
3. Lines 179-181 should say "Files are just saved to disk"

**Fix**:

```python
# WRONG ❌
from ..services.pdf_parser import pdf_parser_service
# ... processing during upload

# CORRECT ✅
# Files are just saved to disk - no processing until analysis
```

---

### **Issue 2: No processing during analysis**

**Symptom**: Files remain `"pending"` after analysis, no data extracted.

**Cause**: PDF parser not called in analysis pipeline.

**Solution**:

1. Check `backend/app/api/analysis.py` line 8
2. SHOULD import `pdf_parser_service`
3. Lines 120-175 should have PDF processing code

**Fix**:

```python
# CORRECT ✅
from ..services.pdf_parser import pdf_parser_service

# In run_validation_pipeline():
parsing_result = pdf_parser_service.parse_traveler_pdf(traveler_file.storage_path)
```

---

### **Issue 3: Low completeness score (< 50%)**

**Symptom**: Score shows 30%, but PDF looks complete.

**Common Causes**:

1. **Scanned PDF without OCR**: PDF is an image, not searchable text
2. **Non-standard format**: Doesn't follow expected Traveler structure
3. **Missing key sections**: No "Seq 20" or job number clearly labeled

**Solutions**:

```bash
# Check if PDF has searchable text
# Open PDF, try to copy/paste text
# If you can't copy text → it's a scanned image

# Re-export PDF from source system
# Use "Save as PDF" not "Print to PDF"
# Ensure text is searchable
```

**Check Logs**:

```bash
# View extraction details
tail -f backend/logs/app.log

# Look for warnings
grep "WARNING" backend/logs/app.log
```

---

### **Issue 4: Empty board_serials array**

**Symptom**: `"board_serials": []` even though serials are in PDF.

**Common Causes**:

1. Serials not in "Seq 20" section
2. Format doesn't match patterns (e.g., `12345_6789` with underscore)
3. Serials split across multiple lines

**Solutions**:

- Ensure serials are in format: `12345-6789` or `VGN-12345-6789`
- Place serials in or near "Seq 20" section
- Keep serials on one line (not split)

**Test Pattern**:

```python
# Valid formats
"12345-6789"      ✅
"VGN-12345-6789"  ✅
"vgn-12345-6789"  ✅

# Invalid formats
"123456789"       ❌ (no hyphen)
"12345_6789"      ❌ (underscore)
"VGN 12345-6789"  ❌ (space instead of hyphen)
```

---

### **Issue 5: SQL queries in console**

**Symptom**: Console shows database queries like `SELECT * FROM...`

**Cause**: SQL logging not disabled.

**Solution**:
Check `backend/app/logging_config.py` line 77:

```python
# Should be WARNING level (not INFO or DEBUG)
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
```
