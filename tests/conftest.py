"""
Pytest configuration and fixtures for Physiology RAG System tests.
"""

import os
import tempfile
from pathlib import Path
from typing import Dict, Any, List

import pytest

from physiology_rag.config.settings import Settings


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def test_settings(temp_dir):
    """Create test settings with temporary directories."""
    return Settings(
        gemini_api_key="test-api-key",
        data_dir=str(temp_dir / "data"),
        vector_db_path=str(temp_dir / "vector_db"),
        chunk_size=500,  # Smaller for testing
        log_level="DEBUG"
    )


@pytest.fixture
def sample_document():
    """Sample document data for testing."""
    return {
        'document_name': 'Test Document',
        'content': 'This is a test document about the cerebral cortex. The cerebral cortex is the outermost layer of the brain.',
        'chunks': [
            {
                'text': 'This is a test document about the cerebral cortex.',
                'type': 'section',
                'title': 'Introduction',
                'page_id': 1,
                'size': 50
            },
            {
                'text': 'The cerebral cortex is the outermost layer of the brain.',
                'type': 'section', 
                'title': 'Structure',
                'page_id': 1,
                'size': 55
            }
        ],
        'images': [],
        'metadata': {
            'table_of_contents': [
                {'title': 'Introduction', 'page_id': 1},
                {'title': 'Structure', 'page_id': 1}
            ]
        },
        'total_chunks': 2,
        'total_images': 0
    }


@pytest.fixture
def sample_documents(sample_document):
    """List of sample documents for testing."""
    return [sample_document]


@pytest.fixture
def mock_gemini_response():
    """Mock response from Gemini API."""
    return {
        'embedding': [0.1] * 768,  # Mock embedding vector
        'text': 'This is a test response from Gemini.'
    }