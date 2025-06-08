"""
Configuration management for the Physiology RAG system.
Uses pydantic-settings for type-safe configuration with environment variables.
"""

import os
from pathlib import Path
from typing import Optional

try:
    from pydantic_settings import BaseSettings
    from pydantic import validator
except ImportError:
    from pydantic import BaseSettings, validator

from dotenv import load_dotenv

# Load .env file from project root
project_root = Path(__file__).parent.parent.parent
env_path = project_root / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    # Fallback to current directory
    load_dotenv()


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # API Configuration
    gemini_api_key: str
    gemini_model_name: str = "gemini-2.0-flash-exp"
    gemini_embedding_model: str = "models/text-embedding-004"
    gemini_pdf_model: str = "gemini-2.5-flash-preview-04-17"
    
    # Database Configuration
    vector_db_path: str = "./data/vector_db"
    collection_name: str = "physiology_documents"
    similarity_metric: str = "cosine"
    
    # Processing Configuration
    chunk_size: int = 1000
    max_context_length: int = 3000
    batch_size: int = 10
    max_retrieval_results: int = 5
    
    # Path Configuration
    data_dir: str = "./data"
    raw_data_dir: str = "./data/raw"
    processed_data_dir: str = "./data/processed"
    uploads_dir: str = "./data/uploads"
    output_dir: str = "./data/processed"
    
    # UI Configuration
    streamlit_title: str = "🧠 Physiology RAG Assistant"
    streamlit_icon: str = "🧠"
    max_upload_size_mb: int = 50
    
    # Logging Configuration
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    @validator('gemini_api_key')
    def validate_api_key(cls, v):
        if not v or v == "your-api-key-here":
            raise ValueError("GEMINI_API_KEY must be set to a valid API key")
        return v
    
    @validator('data_dir', 'raw_data_dir', 'processed_data_dir', 'uploads_dir', 'vector_db_path')
    def create_directories(cls, v):
        """Ensure directories exist."""
        Path(v).mkdir(parents=True, exist_ok=True)
        return v
    
    class Config:
        case_sensitive = False


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get the application settings."""
    return settings


def reload_settings() -> Settings:
    """Reload settings (useful for testing)."""
    global settings
    settings = Settings()
    return settings