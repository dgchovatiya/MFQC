# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .database import init_db
import os

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Automated validation system for manufacturing documentation",
    debug=settings.DEBUG
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
    print(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    
    # Create uploads directory if not exists
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    
    # Initialize database
    init_db()
    print("Database initialized")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    print("Shutting down...")

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION
    }

# Root endpoint
@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/health"
    }

# Include API routers (will be added in Phase 3)
# from .api import sessions, files, analysis, websocket
# app.include_router(sessions.router, prefix="/api/sessions", tags=["sessions"])
# app.include_router(files.router, prefix="/api/files", tags=["files"])
# app.include_router(analysis.router, prefix="/api/analysis", tags=["analysis"])
# app.include_router(websocket.router, prefix="/ws", tags=["websocket"])
