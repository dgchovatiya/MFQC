# Manufacturing QC Cross-Check System (MFQC)

A web application that automates quality control validation for manufacturing documentation, eliminating the need for manual cross-checking across multiple file types.

## 🎯 Project Overview

This system addresses a critical manufacturing pain point: Quality control engineers currently spend 30-60 minutes per unit manually cross-checking:

- **Traveler PDFs** (work instructions with serial numbers)
- **Product Images** (PCB photos requiring magnifying glass inspection)
- **Excel BOM spreadsheets** (as-built bill of materials)

**Goal**: Reduce validation time from 30-60 minutes to 2-3 minutes with 99%+ accuracy.

## 🛠️ Tech Stack

- **Backend**: FastAPI (Python 3.12)
- **Frontend**: React 18 + JavaScript + Material-UI (MUI) *(Coming Soon)*
- **Database**: SQLite
- **Processing**: OCR (Tesseract + OpenCV), PDF parsing (pdfplumber), Excel parsing (pandas)
- **Deployment**: Docker + Docker Compose
- **Real-time**: WebSocket for progress tracking *(Coming Soon)*

## ✨ Key Features

### Core Validation Checks

1. **Job Number Matching** - Traveler vs BOM cross-reference
2. **Part Number Validation** - Ensure all parts exist in BOMs
3. **Revision Comparison** - Detect version mismatches (Rev F vs F2)
4. **Serial Normalization** - Auto-add VGN- and INF- prefixes
5. **Flight Status Detection** - OCR verification of hardware markings
6. **File Completeness** - Ensure all required documents uploaded

### User Experience

- **Drag-and-drop file upload** with real-time validation
- **Progress tracking** via WebSocket during analysis
- **Clear results dashboard** with Pass/Warning/Fail/Info status
- **Evidence viewer** showing source data comparisons
- **Session history** for past validations
- **CSV export** for sharing results with stakeholders

## 📊 Expected Results (Sample Data)

With the provided sample files, the system detects:

- ✅ **Job 82334** found in BOM files
- ✅ All **part numbers** (PCA-1153-03, PCA-1052-05, PCA-1130-03) validated
- ⚠️ **Revision mismatch**: PCA-1153-03 Rev F (main BOM) vs Rev F2 (sub-assembly BOM)
- ℹ️ **Serial normalization**: 1619 → INF-1619, 80751-0053 → VGN-80751-0053
- ✅ **Flight status**: "FLIGHT" marking confirmed

**Overall Result**: ⚠️ **WARNING** (due to minor revision difference)

## 🚀 Quick Start

### Prerequisites

- **Docker** and **Docker Compose** installed on your system
  - [Install Docker Desktop](https://www.docker.com/products/docker-desktop/) (includes Docker Compose)
  - Verify installation: `docker --version` and `docker-compose --version`

### Running the Application

1. **Clone the repository**

   ```bash
   git clone <repository-url>
   cd MFQC
   ```
2. **Start the application**

   ```bash
   docker-compose up --build
   ```
   This will:

   - Build the Docker image with Python 3.12 and Tesseract OCR
   - Install all dependencies automatically
   - Start the FastAPI backend on port 8000
   - Create persistent volumes for uploads, database, and logs
3. **Access the API**

   - **API Documentation (Swagger)**: http://localhost:8000/docs
   - **Alternative Docs (ReDoc)**: http://localhost:8000/redoc
   - **Health Check**: http://localhost:8000/
4. **Stop the application**

   ```bash
   docker-compose down
   ```
