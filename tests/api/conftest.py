"""
API test fixtures and utilities.
"""
import pytest
import tempfile
from pathlib import Path
from fastapi.testclient import TestClient
from physiology_rag.api.main import app
from physiology_rag.config.settings import Settings, get_settings
from physiology_rag.core.rag_system import RAGSystem


@pytest.fixture
def temp_data_dir():
    """Create a temporary directory for test data."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def test_settings_api(temp_data_dir):
    """Create test settings with temporary directories for API tests."""
    return Settings(
        gemini_api_key="test-api-key-for-jwt-generation",
        data_dir=str(temp_data_dir / "data"),
        vector_db_path=str(temp_data_dir / "vector_db"),
        processed_data_dir=str(temp_data_dir / "processed"),
        uploads_dir=str(temp_data_dir / "uploads"),
        chunk_size=100,
        log_level="DEBUG",
        jwt_secret_key="test-jwt-secret-key-for-testing-only"
    )


@pytest.fixture
def client(test_settings_api, monkeypatch):
    """Create a test client with mocked settings."""
    def get_test_settings():
        return test_settings_api
    
    # Override the settings dependency
    monkeypatch.setattr("physiology_rag.config.settings.settings", test_settings_api)
    
    # Initialize mock RAG system for tests
    class MockRAGSystem:
        def retrieve_relevant_chunks(self, query, n_results=5):
            return {
                "results": [
                    {
                        "metadata": {
                            "document_name": "test_doc.pdf",
                            "title": "Test Section",
                            "chunk_index": 0,
                            "page_id": 1
                        },
                        "similarity_score": 0.95,
                        "content": "This is test content about neurons."
                    }
                ]
            }
        
        def answer_question(self, question, n_results=5):
            return {
                "answer": "Test answer about the query.",
                "sources": [
                    {
                        "metadata": {
                            "document_name": "test_doc.pdf",
                            "title": "Test Section",
                            "chunk_index": 0,
                            "page_id": 1
                        },
                        "similarity_score": 0.95,
                        "content": "This is test content about neurons."
                    }
                ]
            }
    
    app.state.rag_system = MockRAGSystem()
    
    return TestClient(app)


@pytest.fixture
def mock_rag_system(monkeypatch):
    """Create a mock RAG system for testing."""
    class MockRAGSystem:
        def retrieve_relevant_chunks(self, query, n_results=5):
            return {
                "results": [
                    {
                        "metadata": {
                            "document_name": "test_doc.pdf",
                            "title": "Test Section",
                            "chunk_index": 0,
                            "page_id": 1
                        },
                        "similarity_score": 0.95,
                        "content": "This is test content about neurons."
                    }
                ]
            }
        
        def answer_question(self, question, n_results=5):
            return {
                "answer": "Test answer about the query.",
                "sources": [
                    {
                        "metadata": {
                            "document_name": "test_doc.pdf",
                            "title": "Test Section",
                            "chunk_index": 0,
                            "page_id": 1
                        },
                        "similarity_score": 0.95,
                        "content": "This is test content about neurons."
                    }
                ]
            }
    
    mock = MockRAGSystem()
    app.state.rag_system = mock
    return mock


@pytest.fixture
def auth_token(client):
    """Get an authentication token for testing."""
    response = client.post("/auth/login")
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture
def auth_headers(auth_token):
    """Get authentication headers for testing."""
    return {"Authorization": f"Bearer {auth_token}"}
