"""
Tests for chat endpoints.
"""
import pytest


def test_chat_message(client, auth_headers, mock_rag_system):
    """Test sending a chat message."""
    response = client.post(
        "/chat",
        headers=auth_headers,
        json={"message": "What is a neuron?", "stream": False}
    )
    assert response.status_code == 200
    
    data = response.json()
    assert "message_id" in data
    assert "response" in data
    assert "intent" in data
    assert "agent_used" in data
    assert "sources" in data
    assert "new_session_token" in data
    assert "metadata" in data


def test_chat_message_without_auth(client):
    """Test that chat requires authentication."""
    response = client.post(
        "/chat",
        json={"message": "What is a neuron?"}
    )
    assert response.status_code == 401


def test_chat_message_empty(client, auth_headers):
    """Test that empty messages are rejected."""
    response = client.post(
        "/chat",
        headers=auth_headers,
        json={"message": ""}
    )
    assert response.status_code == 422  # Validation error


def test_chat_message_too_long(client, auth_headers):
    """Test that very long messages are rejected."""
    response = client.post(
        "/chat",
        headers=auth_headers,
        json={"message": "x" * 5001}  # Over max length
    )
    assert response.status_code == 422  # Validation error


def test_chat_history(client, auth_headers):
    """Test getting chat history."""
    # First send a message
    client.post(
        "/chat",
        headers=auth_headers,
        json={"message": "What is a neuron?"}
    )
    
    # Then get history
    response = client.get("/chat/history", headers=auth_headers)
    assert response.status_code == 200
    
    data = response.json()
    assert "session_id" in data
    assert "interactions" in data
    assert "topics_covered" in data
    assert "new_session_token" in data


def test_chat_history_without_auth(client):
    """Test that chat history requires authentication."""
    response = client.get("/chat/history")
    assert response.status_code == 401


def test_chat_stream_endpoint_returns_501(client, auth_headers):
    """Test that POST streaming endpoint is not implemented."""
    response = client.post(
        "/chat/stream",
        headers=auth_headers,
        json={"message": "What is a neuron?"}
    )
    # The POST endpoint returns 501 Not Implemented
    assert response.status_code == 501  # Not implemented
