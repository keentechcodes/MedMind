"""
Tests for query endpoints.
"""
import pytest


def test_query_documents(client, auth_headers, mock_rag_system):
    """Test performing a RAG query."""
    response = client.post(
        "/query",
        headers=auth_headers,
        json={
            "query": "What is the blood-brain barrier?",
            "n_results": 3,
            "include_sources": True,
            "include_attribution": False
        }
    )
    assert response.status_code == 200
    
    data = response.json()
    assert "answer" in data
    assert "sources" in data
    assert "attribution" in data
    assert "query_time_ms" in data
    assert "new_session_token" in data
    assert len(data["sources"]) > 0


def test_query_without_auth(client):
    """Test that query requires authentication."""
    response = client.post(
        "/query",
        json={"query": "What is a neuron?"}
    )
    assert response.status_code == 401


def test_query_empty(client, auth_headers):
    """Test that empty queries are rejected."""
    response = client.post(
        "/query",
        headers=auth_headers,
        json={"query": ""}
    )
    assert response.status_code == 422


def test_query_n_results_validation(client, auth_headers):
    """Test n_results parameter validation."""
    # Too few results
    response = client.post(
        "/query",
        headers=auth_headers,
        json={"query": "test", "n_results": 0}
    )
    assert response.status_code == 422
    
    # Too many results
    response = client.post(
        "/query",
        headers=auth_headers,
        json={"query": "test", "n_results": 11}
    )
    assert response.status_code == 422


def test_search_documents(client, auth_headers, mock_rag_system):
    """Test searching documents."""
    response = client.get(
        "/query/search?q=neuron&limit=5",
        headers=auth_headers
    )
    assert response.status_code == 200
    
    data = response.json()
    assert "query" in data
    assert "results" in data
    assert "total" in data
    assert "new_session_token" in data
    assert data["query"] == "neuron"


def test_search_without_query_param(client, auth_headers):
    """Test that search requires query parameter."""
    response = client.get("/query/search", headers=auth_headers)
    assert response.status_code == 422


def test_search_limit_validation(client, auth_headers):
    """Test limit parameter validation."""
    # Too few
    response = client.get(
        "/query/search?q=test&limit=0",
        headers=auth_headers
    )
    assert response.status_code == 422
    
    # Too many
    response = client.get(
        "/query/search?q=test&limit=21",
        headers=auth_headers
    )
    assert response.status_code == 422


def test_search_without_auth(client):
    """Test that search requires authentication."""
    response = client.get("/query/search?q=neuron")
    assert response.status_code == 401
