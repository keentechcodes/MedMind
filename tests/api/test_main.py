"""
Tests for main API endpoints (health, root).
"""
import pytest


def test_health_check(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "healthy"
    assert "rag_system" in data
    assert "version" in data


def test_root_endpoint(client):
    """Test root endpoint returns API info."""
    response = client.get("/")
    assert response.status_code == 200
    
    data = response.json()
    assert data["name"] == "MedMind API"
    assert "version" in data
    assert "endpoints" in data
    assert "docs" in data
    assert "/auth" in data["endpoints"].values()
    assert "/chat" in data["endpoints"].values()
    assert "/query" in data["endpoints"].values()


def test_openapi_schema(client):
    """Test OpenAPI schema is accessible."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    
    data = response.json()
    assert data["info"]["title"] == "MedMind API"
    assert "paths" in data
    assert "/health" in data["paths"]
    assert "/auth/login" in data["paths"]
    assert "/chat" in data["paths"]
