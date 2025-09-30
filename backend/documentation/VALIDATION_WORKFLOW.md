# Manufacturing QC Validation Workflow

## Overview

The Manufacturing QC Cross-Check System performs 7 priority-ordered validation checks to ensure manufacturing documentation accuracy and completeness.

## Input Files Required

### 1. Traveler PDF
- **Purpose**: Work instruction document with job numbers and serial data
- **Format**: `.pdf`
- **Key Data**: Job number, unit serial, board serials, part numbers
- **Sample**: `DRW-1608-03_Traveler.pdf`

### 2. Product Image  
- **Purpose**: Photo of assembled hardware with visible markings
- **Format**: `.jpg`, `.jpeg`, `.png`
- **Key Data**: Unit serial (INF-####), board serials (VGN-#####-####), flight status
- **Sample**: `Hardware_Photo_INF1619.jpg`

### 3. BOM Excel Files
- **Purpose**: As-built bill of materials with part specifications
- **Format**: `.xlsx`, `.xlsm`
- **Key Data**: Job numbers (Column A), part numbers (Column B), revisions (Column H)
- **Sample**: `As_Built_82334.xlsx`, `As_Built_80751.xlsm`

---

## Validation Checks (Priority Order)

### Check 1: Job Number Match (CRITICAL)
**Priority**: 1  
**Logic**: Traveler job number must exist in at least one BOM file  
**Status**: PASS/FAIL

**Example**:
- Traveler: Job 82334  
- BOM Files: Jobs 80641, 80751, 82334 ✅  
- Result: **PASS** - "Job 82334 found in BOM"

**Failure Case**:
- Traveler: Job 99999
- BOM Files: Jobs 80641, 80751, 82334
- Result: **FAIL** - "Job 99999 not found in any BOM"

### Check 2: Part Numbers Match (CRITICAL)
**Priority**: 2  
**Logic**: Every part number from Traveler/Image must exist in BOM files  
**Status**: PASS/FAIL (per part)

**Example**:
- Traveler/Image: PCA-1153-03, PCA-1052-05, PCA-1130-03
- BOM Parts: PCA-1153-03, PCA-1052-05, PCA-1130-03, HOUSING-001
- Result: **PASS** - "All parts found in BOM"

**Failure Case**:
- Traveler: PCA-1153-03, PCA-9999-99
- BOM Parts: PCA-1153-03, PCA-1052-05  
- Result: **FAIL** - "PCA-9999-99 in Traveler but missing in all BOMs"

### Check 3: Revisions Match (MODERATE)
**Priority**: 3  
**Logic**: Part revisions should match, with tolerance for format differences  
**Status**: PASS/WARNING/FAIL

**Normalization Rules**:
- Remove "Rev" prefix: "Rev F2" → "F2"
- Uppercase: "f2" → "F2"
- Strip whitespace

**Warning Example**:
- Image/Traveler: PCA-1153-03 Rev F
- BOM (Job 82334): PCA-1153-03 Rev F ✅  
- BOM (Job 80751): PCA-1153-03 Rev F2 ⚠️
- Result: **WARNING** - "PCA-1153-03: Rev F vs Rev F2 (minor difference)"

### Check 4: Board Serials Match (MODERATE)  
**Priority**: 4  
**Logic**: Board serials must match after normalization  
**Status**: PASS/INFO/FAIL

**Normalization Rules**:
- Add VGN- prefix if missing
- Case-insensitive comparison
- Format: VGN-#####-####

**Info Example**:
- Traveler: 80751-0053 (missing prefix)
- Image: VGN-80751-0053 (complete)  
- Result: **INFO** - "Board serial normalized to VGN-80751-0053 (matches image)"

### Check 5: Unit Serial Match (MODERATE)
**Priority**: 5  
**Logic**: Unit serial must match after normalization  
**Status**: PASS/INFO/FAIL

**Normalization Rules**:
- Add INF- prefix if missing
- Case-insensitive comparison  
- Format: INF-####

**Info Example**:
- Traveler: 1619 (missing prefix)
- Image: INF-1619 (complete)
- Result: **INFO** - "Unit serial normalized to INF-1619 (matches image)"

### Check 6: Flight Status (INFORMATIONAL)
**Priority**: 6  
**Logic**: Detect and report flight status from image OCR  
**Status**: PASS/WARNING/FAIL

**Expected Markings**:
- `FLIGHT` → **PASS** - "Flight-qualified hardware confirmed"
- `EDU – NOT FOR FLIGHT` → **WARNING** - "Educational hardware (not flight-qualified)"  
- Neither found → **FAIL** - "Flight status marking not detected"

### Check 7: File Completeness (CRITICAL)
**Priority**: 7  
**Logic**: Ensure all required files are present and readable  
**Status**: PASS/WARNING/FAIL

**Required Files**:
- 1 Traveler PDF
- 1 Product Image
- 1-4 Excel BOMs

**Example**:
- Uploaded: 1 PDF, 1 JPG, 3 Excel ✅
- Result: **PASS** - "All required files present"

---

## Status Determination Logic

### Individual Check Status
- **PASS**: Check completed successfully
- **WARNING**: Minor discrepancies that may be acceptable  
- **FAIL**: Critical mismatches found
- **INFO**: Informational notice (e.g., normalization applied)

### Overall Session Result
```
IF any check = FAIL:
    overall_status = FAIL
ELIF any check = WARNING:  
    overall_status = WARNING
ELSE:
    overall_status = PASS
```

**Status Hierarchy**: FAIL > WARNING > PASS > INFO

### Shipping Decisions
- **PASS**: Ship hardware ✅
- **WARNING**: Review required ⚠️  
- **FAIL**: Hold shipment ❌

---

## Sample Data Expected Results

**Given Sample Files**:
- Traveler PDF: Job 82334, DRW-1608-03 Rev B
- Product Image: INF-1619, FLIGHT marking
- Excel BOMs: Jobs 82334, 80751, 80641

**Expected Validation Results**:
```
OVERALL STATUS: ⚠️ WARNING

✓ Check 1: Job Number Match - PASS
  "Job 82334 found in BOM file"

✓ Check 2: Part Numbers Match - PASS  
  "All part numbers found in BOMs"

⚠️ Check 3: Revision Match - WARNING
  "PCA-1153-03: Rev F (main BOM) vs Rev F2 (sub-assembly BOM)"

ℹ️ Check 4: Board Serials Match - INFO
  "Board serials normalized (VGN- prefix added)"

ℹ️ Check 5: Unit Serial Match - INFO  
  "Unit serial normalized: 1619 → INF-1619"

✓ Check 6: Flight Status - PASS
  "FLIGHT marking confirmed"

✓ Check 7: File Completeness - PASS
  "All required files present (1 PDF, 1 image, 3 Excel)"
```

**Shipping Decision**: Review Required (due to revision mismatch)
