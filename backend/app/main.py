# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .database import init_db
from .logging_config import setup_logging
import os

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
    ## Manufacturing QC Cross-Check System

    Automated validation system for manufacturing documentation that eliminates manual cross-checking across multiple file types.

    ### Features:
    * **File Processing**: Handles Traveler PDFs, Product Images, and Excel BOMs
    * **7 Validation Checks**: Priority-ordered quality control validation
    * **Status Tracking**: Real-time progress monitoring
    * **Evidence Collection**: Detailed audit trails for compliance

    ### Workflow:
    1. Create a new analysis session
    2. Upload required files (PDF, Image, Excel)
    3. Trigger analysis pipeline
    4. Retrieve validation results with evidence

    ### File Requirements:
    * **Traveler PDF**: Work instructions with job numbers and serials
    * **Product Image**: Hardware photos with OCR-readable markings
    * **BOM Excel**: As-built bill of materials (.xlsx/.xlsm)

    ### Validation Results:
    * **PASS**: All checks successful ✅
    * **WARNING**: Minor discrepancies requiring review ⚠️
    * **FAIL**: Critical issues preventing shipment ❌
    * **INFO**: Informational notices (normalization applied) ℹ️
    """,
    debug=settings.DEBUG,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {
            "name": "sessions",
            "description": "Session management - Create, list, and manage analysis sessions"
        },
        {
            "name": "files", 
            "description": "File operations - Upload and manage manufacturing documents"
        },
        {
            "name": "analysis",
            "description": "Analysis pipeline - Trigger and monitor validation processing"
        },
        {
            "name": "results",
            "description": "Validation results - Retrieve analysis outcomes and evidence"
        },
        {
            "name": "system",
            "description": "System endpoints - Health checks and API information"
        }
    ]
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize database and create upload directory"""
    # Setup logging first (creates log files)
    logger = setup_logging()
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    
    # Create uploads directory if not exists
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    logger.info(f"Upload directory: {settings.UPLOAD_DIR}")
    
    # Initialize database
    init_db()
    logger.info("Database initialized successfully")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    import logging
    logger = logging.getLogger(__name__)
    logger.info("Shutting down Manufacturing QC System...")

# Health check endpoint
@app.get("/health", tags=["system"])
async def health_check():
    """
    System Health Check
    
    Returns the current system status and version information.
    Used by monitoring systems and load balancers.
    """
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION
    }

# Root endpoint
@app.get("/", tags=["system"])
async def root():
    """
    API Root Information
    
    Welcome endpoint with basic API information and navigation links.
    Provides links to documentation and health check endpoints.
    """
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/health"
    }

# Include API routers
from .api import sessions, files, analysis, results

app.include_router(sessions.router, prefix="/api/sessions", tags=["sessions"])
app.include_router(files.router, prefix="/api/sessions", tags=["files"])
app.include_router(analysis.router, prefix="/api/sessions", tags=["analysis"])
app.include_router(results.router, prefix="/api/sessions", tags=["results"])
