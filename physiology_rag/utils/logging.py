"""
Logging configuration for the Physiology RAG system.
"""

import logging
import sys
from pathlib import Path
from typing import Optional

from ..config.settings import get_settings


def setup_logging(
    name: Optional[str] = None,
    level: Optional[str] = None,
    log_file: Optional[Path] = None
) -> logging.Logger:
    """
    Set up logging for the application.
    
    Args:
        name: Logger name (defaults to package name)
        level: Log level (defaults to settings.log_level)
        log_file: Optional log file path
        
    Returns:
        Configured logger instance
    """
    settings = get_settings()
    
    # Get logger
    logger_name = name or "physiology_rag"
    logger = logging.getLogger(logger_name)
    
    # Set level
    log_level = level or settings.log_level
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Create formatter
    formatter = logging.Formatter(settings.log_format)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (optional)
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger for a specific module."""
    return logging.getLogger(f"physiology_rag.{name}")