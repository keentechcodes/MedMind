"""
Tests for document endpoints.
"""
import pytest
import json
from datetime import datetime


def test_list_documents(client, auth_headers, temp_data_dir):
    """Test listing documents."""
    # Create a mock processed documents file
    processed_file = temp_data_dir / "processed" / "processed_documents.json"
    processed_file.parent.mkdir(parents=True, exist_ok=True)
    
    test_docs = [
        {
            "document_name": "test_doc.pdf",
            "total_chunks": 10,
            "total_images": 2,
            "processing_date": datetime.now().isoformat()
        }
    ]
    
    with open(processed_file, "w") as f:
        json.dump(test_docs, f)
    
    response = client.get("/documents", headers=auth_headers)
    assert response.status_code == 200
    
    data = response.json()
    assert "documents" in data
    assert "total" in data
    assert "new_session_token" in data
    assert data["total"] == 1


def test_list_documents_empty(client, auth_headers):
    """Test listing documents when none exist."""
    response = client.get("/documents", headers=auth_headers)
    assert response.status_code == 200
    
    data = response.json()
    assert data["documents"] == []
    assert data["total"] == 0


def test_list_documents_without_auth(client):
    """Test that listing documents requires authentication."""
    response = client.get("/documents")
    assert response.status_code == 401


def test_upload_document_pdf(client, auth_headers, temp_data_dir):
    """Test uploading a PDF document."""
    # Create a simple test PDF (just the header bytes)
    pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\nxref\ntrailer\n<<\n/Size 1\n/Root 1 0 R\n>>\nstartxref\n0\n%%EOF"
    
    response = client.post(
        "/documents/upload",
        headers=auth_headers,
        files={"file": ("test.pdf", pdf_content, "application/pdf")}
    )
    assert response.status_code == 200
    
    data = response.json()
    assert "job_id" in data
    assert "status" in data
    assert data["status"] == "processing"
    assert "filename" in data
    assert "message" in data
    assert "new_session_token" in data


def test_upload_document_invalid_extension(client, auth_headers):
    """Test that non-PDF files are rejected."""
    response = client.post(
        "/documents/upload",
        headers=auth_headers,
        files={"file": ("test.txt", b"Not a PDF", "text/plain")}
    )
    assert response.status_code == 400
    assert "detail" in response.json()


def test_upload_document_path_traversal(client, auth_headers):
    """Test that path traversal attempts are blocked."""
    response = client.post(
        "/documents/upload",
        headers=auth_headers,
        files={"file": ("../etc/passwd.pdf", b"%PDF-1.4\n", "application/pdf")}
    )
    assert response.status_code == 400


def test_upload_without_auth(client):
    """Test that upload requires authentication."""
    pdf_content = b"%PDF-1.4\n"
    response = client.post(
        "/documents/upload",
        files={"file": ("test.pdf", pdf_content, "application/pdf")}
    )
    assert response.status_code == 401


def test_get_upload_status(client, auth_headers, temp_data_dir):
    """Test checking upload status."""
    # First upload a document
    pdf_content = b"%PDF-1.4\n"
    upload_response = client.post(
        "/documents/upload",
        headers=auth_headers,
        files={"file": ("test.pdf", pdf_content, "application/pdf")}
    )
    
    job_id = upload_response.json()["job_id"]
    
    # Check status
    response = client.get(f"/documents/upload/status/{job_id}", headers=auth_headers)
    assert response.status_code == 200
    
    data = response.json()
    assert "job_id" in data
    assert "status" in data
    assert "progress" in data


def test_get_upload_status_not_found(client, auth_headers):
    """Test checking status of non-existent job."""
    response = client.get(
        "/documents/upload/status/non-existent-job",
        headers=auth_headers
    )
    assert response.status_code == 404


def test_delete_document(client, auth_headers, temp_data_dir):
    """Test deleting a document."""
    # Create a mock processed documents file
    processed_file = temp_data_dir / "processed" / "processed_documents.json"
    processed_file.parent.mkdir(parents=True, exist_ok=True)
    
    test_docs = [
        {
            "document_name": "test_doc.pdf",
            "total_chunks": 10,
            "total_images": 2,
            "processing_date": datetime.now().isoformat()
        }
    ]
    
    with open(processed_file, "w") as f:
        json.dump(test_docs, f)
    
    response = client.delete("/documents/test_doc.pdf", headers=auth_headers)
    assert response.status_code == 200
    
    data = response.json()
    assert "message" in data
    assert "new_session_token" in data


def test_delete_document_not_found(client, auth_headers):
    """Test deleting a non-existent document."""
    response = client.delete("/documents/nonexistent.pdf", headers=auth_headers)
    assert response.status_code == 404


def test_get_document_detail(client, auth_headers, temp_data_dir):
    """Test getting document details."""
    # Create a mock processed documents file
    processed_file = temp_data_dir / "processed" / "processed_documents.json"
    processed_file.parent.mkdir(parents=True, exist_ok=True)
    
    test_docs = [
        {
            "document_name": "test_doc.pdf",
            "total_chunks": 10,
            "total_images": 2,
            "processing_date": datetime.now().isoformat()
        }
    ]
    
    with open(processed_file, "w") as f:
        json.dump(test_docs, f)
    
    response = client.get("/documents/test_doc.pdf", headers=auth_headers)
    assert response.status_code == 200
    
    data = response.json()
    assert "document" in data
    assert "new_session_token" in data
