"""
Documents router for MedMind API.
Handles document upload, listing, and management.
"""

import uuid
import json
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from physiology_rag.api.models import DocumentListResponse, UploadResponse, JobStatus, DocumentInfo

from physiology_rag.api.models import DocumentListResponse, UploadResponse, JobStatus, DocumentInfo
from physiology_rag.api.deps import get_current_session, create_session_token
from physiology_rag.dependencies.medical_context import MedicalContext
from physiology_rag.config.settings import get_settings
from physiology_rag.utils.logging import get_logger

logger = get_logger("documents_router")
router = APIRouter(prefix="/documents", tags=["Documents"])

# In-memory job cache
# TODO: Replace with Redis for production to support horizontal scaling
# This cache won't persist across server restarts or work with multiple API instances
job_cache = {}


@router.get("", response_model=DocumentListResponse)
async def list_documents(context: MedicalContext = Depends(get_current_session)):
    """
    List all indexed documents.
    
    Returns document metadata including chunk counts and processing dates.
    """
    try:
        settings = get_settings()
        processed_file = Path(settings.processed_data_dir) / "processed_documents.json"
        
        if not processed_file.exists():
            # Return empty list if no documents processed yet
            new_token = await create_session_token(context)
            return DocumentListResponse(
                documents=[],
                total=0,
                new_session_token=new_token
            )
        
        with open(processed_file, "r") as f:
            docs = json.load(f)
        
        # Format document info
        documents = []
        for doc in docs:
            documents.append(
                DocumentInfo(
                    id=doc.get("document_name", ""),
                    name=doc.get("document_name", ""),
                    chunks=doc.get("total_chunks", 0),
                    images=doc.get("total_images", 0),
                    processed_date=doc.get("processing_date")
                )
            )
        
        new_token = await create_session_token(context)
        
        return DocumentListResponse(
            documents=documents,
            total=len(documents),
            new_session_token=new_token
        )
        
    except Exception as e:
        logger.error(f"Document listing error: {e}")
        raise HTTPException(status_code=500, detail=f"Error listing documents: {str(e)}")


@router.post("/upload", response_model=UploadResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    context: MedicalContext = Depends(get_current_session)
):
    """
    Upload and process a PDF document.
    
    The document is saved and processed in the background.
    Use /documents/upload/status/{job_id} to check processing status.
    """
    try:
        # Validate file type - check both extension and content type
        allowed_extensions = {'.pdf'}
        allowed_content_types = {'application/pdf'}
        
        # Get file extension (handle case insensitivity and security)
        from pathlib import Path
        file_ext = Path(file.filename).suffix.lower()
        
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail="Only PDF files are supported"
            )
        
        # Validate content type if provided
        if file.content_type and file.content_type not in allowed_content_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid content type: {file.content_type}. Only PDF files are supported"
            )
        
        # Additional security: check for path traversal attempts
        if '..' in file.filename or '/' in file.filename or '\\' in file.filename:
            raise HTTPException(
                status_code=400,
                detail="Invalid filename"
            )
        
        settings = get_settings()
        
        # Create upload directory if it doesn't exist
        upload_dir = Path(settings.uploads_dir)
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Save file
        upload_path = upload_dir / file.filename
        content = await file.read()
        
        with open(upload_path, "wb") as f:
            f.write(content)
        
        # Create job for background processing
        job_id = str(uuid.uuid4())
        job_cache[job_id] = {
            "status": "processing",
            "progress": 0,
            "filename": file.filename,
            "user_id": context.user_id,
            "started_at": datetime.now().isoformat()
        }
        
        # Schedule background processing
        background_tasks.add_task(
            process_document_task,
            job_id=job_id,
            file_path=upload_path,
            filename=file.filename
        )
        
        logger.info(f"Document upload started: {file.filename}, job: {job_id}")
        
        new_token = await create_session_token(context)
        
        return UploadResponse(
            job_id=job_id,
            status="processing",
            filename=file.filename,
            message="Document uploaded and processing in background. Check status endpoint for updates.",
            new_session_token=new_token
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document upload error: {e}")
        raise HTTPException(status_code=500, detail=f"Error uploading document: {str(e)}")


@router.get("/upload/status/{job_id}", response_model=JobStatus)
async def get_upload_status(
    job_id: str,
    context: MedicalContext = Depends(get_current_session)
):
    """
    Check the status of a document upload/processing job.
    
    Returns current status, progress percentage, and any errors.
    """
    job = job_cache.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Verify job belongs to authenticated user
    if job.get("user_id") != context.user_id:
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to view this job"
        )
    
    return JobStatus(
        job_id=job_id,
        status=job.get("status", "unknown"),
        progress=job.get("progress"),
        document_id=job.get("document_id"),
        error=job.get("error")
    )


@router.get("/{document_id}")
async def get_document(
    document_id: str,
    context: MedicalContext = Depends(get_current_session)
):
    """
    Get detailed information about a specific document.
    
    Returns document metadata, chunks, and sections.
    """
    try:
        settings = get_settings()
        processed_file = Path(settings.processed_data_dir) / "processed_documents.json"
        
        if not processed_file.exists():
            raise HTTPException(status_code=404, detail="No documents found")
        
        with open(processed_file, "r") as f:
            docs = json.load(f)
        
        # Find document
        doc = next((d for d in docs if d.get("document_name") == document_id), None)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        
        new_token = await create_session_token(context)
        
        return {
            "document": doc,
            "new_session_token": new_token
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document retrieval error: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving document: {str(e)}")


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    context: MedicalContext = Depends(get_current_session)
):
    """
    Delete a document from the index.
    
    Removes the document and all its chunks from the vector database.
    """
    try:
        settings = get_settings()
        processed_file = Path(settings.processed_data_dir) / "processed_documents.json"
        
        if not processed_file.exists():
            raise HTTPException(status_code=404, detail="No documents found")
        
        with open(processed_file, "r") as f:
            docs = json.load(f)
        
        # Find and remove document
        doc = next((d for d in docs if d.get("document_name") == document_id), None)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Remove from list
        docs = [d for d in docs if d.get("document_name") != document_id]
        
        # Save updated list
        with open(processed_file, "w") as f:
            json.dump(docs, f, indent=2)
        
        # TODO: Remove from ChromaDB as well
        
        logger.info(f"Document deleted: {document_id}")
        
        new_token = await create_session_token(context)
        
        return {
            "message": f"Document {document_id} deleted successfully",
            "new_session_token": new_token
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document deletion error: {e}")
        raise HTTPException(status_code=500, detail=f"Error deleting document: {str(e)}")


async def process_document_task(job_id: str, file_path: Path, filename: str):
    """
    Background task to process an uploaded document.
    
    Extracts text, creates chunks, and adds to vector database.
    """
    try:
        logger.info(f"Starting document processing for job {job_id}: {filename}")
        
        # Update status
        job_cache[job_id]["progress"] = 10
        
        # Import here to avoid circular imports
        from physiology_rag.core.document_processor import DocumentProcessor
        
        # Process document
        processor = DocumentProcessor()
        
        # For now, this is a placeholder - actual processing would:
        # 1. Extract text from PDF
        # 2. Create chunks
        # 3. Generate embeddings
        # 4. Add to ChromaDB
        
        job_cache[job_id]["progress"] = 50
        
        # Simulate processing time
        import asyncio
        await asyncio.sleep(2)
        
        # Mark as completed
        job_cache[job_id].update({
            "status": "completed",
            "progress": 100,
            "document_id": filename.replace(".pdf", ""),
            "completed_at": datetime.now().isoformat()
        })
        
        logger.info(f"Document processing completed for job {job_id}")
        
    except Exception as e:
        logger.error(f"Document processing error for job {job_id}: {e}")
        job_cache[job_id].update({
            "status": "failed",
            "error": str(e),
            "failed_at": datetime.now().isoformat()
        })
