# app/database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .config import settings

# Create database engine
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
    echo=False  # Disable SQL query logging (too verbose)
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()

# Dependency for FastAPI routes
def get_db():
    """
    Database session dependency
    Usage in routes:
        @app.get("/example")
        def example(db: Session = Depends(get_db)):
            # use db here
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Function to initialize database (creates tables)
def init_db():
    """
    Initialize database by creating all tables
    Called from main.py on startup
    """
    from .models import session, file, result  # Import all models
    Base.metadata.create_all(bind=engine)
