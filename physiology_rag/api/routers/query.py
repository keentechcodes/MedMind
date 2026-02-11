"""
Query router for MedMind API.
Handles direct RAG queries with optional attribution.
"""

import time
from fastapi import APIRouter, Depends, HTTPException, Query

from physiology_rag.api.models import (
    QueryRequest,
    QueryResponse,
    SourceInfo,
    AttributionData,
    AttributionSegment
)
from physiology_rag.api.deps import get_current_session, create_session_token
from physiology_rag.dependencies.medical_context import MedicalContext
from physiology_rag.utils.logging import get_logger

logger = get_logger("query_router")
router = APIRouter(prefix="/query", tags=["RAG Queries"])


from physiology_rag.utils.text_utils import extract_topics_from_query


@router.post("", response_model=QueryResponse)
async def query_documents(
    request: QueryRequest,
    context: MedicalContext = Depends(get_current_session)
):
    """
    Perform a direct RAG query.
    
    Retrieves relevant documents and generates an answer.
    Optionally includes paragraph-level attribution.
    """
    start_time = time.time()
    
    try:
        rag_system = context.rag_system
        
        # Retrieve and generate answer
        result = rag_system.answer_question(request.query, request.n_results)
        
        response_data = {
            "answer": result.get("answer", ""),
            "sources": [],
            "attribution": None,
            "query_time_ms": (time.time() - start_time) * 1000
        }
        
        # Format sources
        sources_list = []
        for s in result.get("sources", []):
            sources_list.append(
                SourceInfo(
                    document=s["metadata"]["document_name"],
                    title=s["metadata"].get("title", "Content"),
                    score=s["similarity_score"],
                    chunk_index=s["metadata"].get("chunk_index"),
                    page_id=s["metadata"].get("page_id")
                )
            )
        response_data["sources"] = sources_list
        
        # Add paragraph-level attribution if requested
        if request.include_attribution and result.get("sources"):
            try:
                from physiology_rag.core.paragraph_extractor import ParagraphExtractor
                from physiology_rag.core.answer_attribution import AnswerAttributionMapper
                from physiology_rag.config.settings import get_settings
                
                settings = get_settings()
                paragraph_extractor = ParagraphExtractor()
                attribution_mapper = AnswerAttributionMapper(settings.gemini_api_key)
                
                # Extract paragraphs
                paragraphs = paragraph_extractor.extract_paragraphs_from_sources(
                    result.get("sources", [])
                )
                
                # Create attributed answer
                attributed = await attribution_mapper.create_attributed_answer(
                    request.query,
                    response_data["answer"],
                    paragraphs
                )
                
                # Format attribution data
                formatted = attribution_mapper.format_attributed_answer_for_display(attributed)
                
                response_data["attribution"] = AttributionData(
                    attributions=[
                        AttributionSegment(
                            segment=a["segment"],
                            confidence=a["confidence"],
                            type=a["type"],
                            supporting_paragraphs=a["supporting_paragraphs"]
                        )
                        for a in formatted["attributions"]
                    ],
                    overall_confidence=formatted["overall_confidence"],
                    paragraphs=formatted["paragraphs"]
                )
                
            except Exception as e:
                logger.warning(f"Attribution failed: {e}")
                # Continue without attribution
        
        # Update context with topics
        topics = extract_topics_from_query(request.query)
        for topic in topics:
            context.add_current_topic(topic)
        
        # Create new session token
        new_token = await create_session_token(context)
        
        return QueryResponse(
            answer=response_data["answer"],
            sources=response_data["sources"],
            attribution=response_data["attribution"],
            query_time_ms=response_data["query_time_ms"],
            new_session_token=new_token
        )
        
    except Exception as e:
        logger.error(f"Query error: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")


@router.get("/search")
async def search_documents(
    q: str = Query(..., description="Search query", min_length=1),
    limit: int = Query(5, ge=1, le=20),
    context: MedicalContext = Depends(get_current_session)
):
    """
    Search documents without generating an answer.
    
    Returns relevant document chunks with metadata and similarity scores.
    Useful for finding sources before asking a full question.
    """
    try:
        rag_system = context.rag_system
        results = rag_system.retrieve_relevant_chunks(q, limit)
        
        # Update context with topics
        topics = extract_topics_from_query(q)
        for topic in topics:
            context.add_current_topic(topic)
        
        new_token = await create_session_token(context)
        
        return {
            "query": q,
            "results": results.get("results", []),
            "total": len(results.get("results", [])),
            "new_session_token": new_token
        }
        
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=f"Error searching documents: {str(e)}")
