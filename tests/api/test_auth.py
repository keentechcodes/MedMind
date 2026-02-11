"""
Tests for authentication endpoints.
"""
import pytest


def test_login_anonymous(client):
    """Test creating an anonymous session."""
    response = client.post("/auth/login")
    assert response.status_code == 200
    
    data = response.json()
    assert "access_token" in data
    assert "token_type" in data
    assert data["token_type"] == "bearer"
    assert "user_id" in data
    assert data["user_id"].startswith("anon_")
    assert "expires_in" in data
    assert data["expires_in"] == 86400  # 24 hours


def test_login_with_user_id(client):
    """Test creating a session with specific user ID."""
    response = client.post("/auth/login", json={"user_id": "test_user_123"})
    assert response.status_code == 200
    
    data = response.json()
    assert data["user_id"] == "test_user_123"
    assert "access_token" in data


def test_refresh_token(client, auth_headers):
    """Test refreshing an authentication token."""
    response = client.post("/auth/refresh", headers=auth_headers)
    assert response.status_code == 200
    
    data = response.json()
    assert "access_token" in data
    assert "token_type" in data
    assert "user_id" in data
    assert "expires_in" in data


def test_get_current_user(client, auth_headers):
    """Test getting current user information."""
    response = client.get("/auth/me", headers=auth_headers)
    assert response.status_code == 200
    
    data = response.json()
    assert "user_id" in data
    assert "preferences" in data
    assert "current_topics" in data
    assert "learning_objectives" in data
    assert "session_topics" in data


def test_protected_endpoint_without_auth(client):
    """Test that protected endpoints require authentication."""
    response = client.get("/auth/me")
    assert response.status_code == 401
    assert "detail" in response.json()


def test_protected_endpoint_with_invalid_token(client):
    """Test that invalid tokens are rejected."""
    headers = {"Authorization": "Bearer invalid_token"}
    response = client.get("/auth/me", headers=headers)
    assert response.status_code == 401


def test_protected_endpoint_with_expired_token(client):
    """Test that expired tokens are rejected."""
    # Create an expired token manually
    from jose import jwt
    from datetime import datetime, timedelta
    
    expired_token = jwt.encode(
        {
            "sub": "test_user",
            "exp": datetime.utcnow() - timedelta(hours=1),
            "iat": datetime.utcnow() - timedelta(hours=2),
            "type": "access"
        },
        "test-jwt-secret-key-for-testing-only",
        algorithm="HS256"
    )
    
    headers = {"Authorization": f"Bearer {expired_token}"}
    response = client.get("/auth/me", headers=headers)
    assert response.status_code == 401
