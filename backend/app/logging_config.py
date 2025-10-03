"""
Logging configuration for Manufacturing QC System

Sets up file-based logging with rotation:
- app.log: General application logs (INFO and above)
- error.log: Error logs only (ERROR and above)
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

def setup_logging():
    """
    Configure application-wide logging
    
    Creates two log files:
    - logs/app.log: All application logs (INFO, WARNING, ERROR)
    - logs/error.log: Error logs only (ERROR, CRITICAL)
    
    Both files rotate at 10MB with 5 backup files kept.
    Console output shows only WARNING and above.
    """
    
    # Create logs directory if it doesn't exist
    log_dir = Path(__file__).parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)
    
    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Clear any existing handlers
    root_logger.handlers.clear()
    
    # Format for log messages
    detailed_formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)-8s [%(name)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)-8s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # 1. General application log file (INFO and above)
    # Rotates at 10MB, keeps 5 backup files
    app_log_file = log_dir / "app.log"
    file_handler = RotatingFileHandler(
        app_log_file,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(file_handler)
    
    # 2. Error log file (ERROR and above only)
    # Rotates at 10MB, keeps 5 backup files
    error_log_file = log_dir / "error.log"
    error_handler = RotatingFileHandler(
        error_log_file,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(error_handler)
    
    # 3. Console output (WARNING and above only)
    # Less verbose for production use
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(simple_formatter)
    root_logger.addHandler(console_handler)
    
    # Disable SQLAlchemy query logging (too verbose)
    # Only show SQLAlchemy warnings and errors
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy.pool').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy.dialects').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy.orm').setLevel(logging.WARNING)
    
    # Disable uvicorn access logs (HTTP requests)
    # These clutter the logs - use only for debugging
    logging.getLogger('uvicorn.access').setLevel(logging.WARNING)
    
    # Log startup message
    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("Manufacturing QC System - Logging Initialized")
    logger.info(f"Application logs: {app_log_file}")
    logger.info(f"Error logs: {error_log_file}")
    logger.info("=" * 60)
    
    return logger


