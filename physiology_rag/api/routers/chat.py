"""
Chat router for MedMind API.
Handles chat messages with SSE streaming support.
"""

import asyncio
import json
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from physiology_rag.api.models import (
    ChatRequest,
    ChatResponse,
    ChatHistoryResponse,
    SourceInfo
)
from physiology_rag.api.deps import get_current_session, create_session_token, security
from physiology_rag.agents.coordinator import CoordinatorAgent
from physiology_rag.dependencies.medical_context import MedicalContext
from physiology_rag.utils.logging import get_logger

logger = get_logger("chat_router")
router = APIRouter(prefix="/chat", tags=["Chat"])


from physiology_rag.utils.text_utils import extract_topics_from_query


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    context: MedicalContext = Depends(get_current_session)
):
    """
    Send a chat message and get a response.
    
    The response includes the AI's answer, source documents,
    and a new session token with updated context state.
    
    For streaming responses, use /chat/stream endpoint instead.
    """
    try:
        coordinator = CoordinatorAgent()
        
        # Parse intent
        intent = coordinator._parse_learning_intent(request.message, context)
        logger.info(f"Intent detected: {intent.intent_type} for user {context.user_id}")
        
        # Handle based on intent type
        if intent.intent_type == "explanation":
            response_data = await handle_explanation(request.message, context)
            agent_used = "tutor"
        else:
            # General conversation
            response_text = await coordinator.handle_conversation(request.message, context)
            response_data = {
                "response": response_text,
                "sources": []
            }
            agent_used = "coordinator"
        
        # Update context with topics
        topics = extract_topics_from_query(request.message)
        for topic in topics:
            context.add_current_topic(topic)
        
        # Create new session token
        new_token = await create_session_token(context)
        
        # Format sources
        sources = [
            SourceInfo(
                document=s["metadata"]["document_name"],
                title=s["metadata"].get("title", "Content"),
                score=s["similarity_score"],
                chunk_index=s["metadata"].get("chunk_index"),
                page_id=s["metadata"].get("page_id")
            )
            for s in response_data.get("sources", [])
        ]
        
        return ChatResponse(
            message_id=str(uuid.uuid4()),
            response=response_data["response"],
            intent=intent.intent_type,
            agent_used=agent_used,
            sources=sources,
            new_session_token=new_token,
            metadata={
                "topics": context.current_topics,
                "interactions": len(context.session_history.user_messages)
            }
        )
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail="Error processing chat request")


@router.post("/stream")
async def chat_stream(request: ChatRequest):
    """
    Stream chat response using Server-Sent Events (SSE).
    
    Returns a stream of events:
    - intent: Detected intent type
    - sources: Retrieved source documents
    - token: Individual response tokens (streaming)
    - complete: Final response with metadata
    - error: Any errors encountered
    
    Client should handle reconnection and token refresh.
    """
    # We need to handle auth manually here since we can't use Depends with streaming
    from fastapi.security import HTTPAuthorizationCredentials
    from physiology_rag.api.deps import security, get_current_session
    
    # This is a workaround - in production you might want to handle this differently
    raise HTTPException(
        status_code=501,
        detail="Streaming endpoint requires WebSocket or manual auth handling. Use /chat instead."
    )


@router.get("/stream-alt")
async def chat_stream_alt(
    message: str,
    credentials=Depends(security)
):
    """
    Alternative streaming endpoint using query parameters for easy testing.
    
    Connect with: GET /chat/stream-alt?message=your+question
    Authorization: Bearer <token>
    
    Returns SSE stream with response tokens.
    """
    from physiology_rag.api.deps import get_current_session
    
    # Get context from auth
    context = await get_current_session(credentials)
    
    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            coordinator = CoordinatorAgent()
            intent = coordinator._parse_learning_intent(message, context)
            
            # Send intent detection
            yield f"data: {json.dumps({'type': 'intent', 'intent': intent.intent_type})}\n\n"
            await asyncio.sleep(0.1)
            
            if intent.intent_type in ["explanation", "general"]:
                # Stream RAG response
                rag_system = context.rag_system
                
                # Retrieve sources
                yield f"data: {json.dumps({'type': 'status', 'message': 'Searching documents...'})}\n\n"
                sources = rag_system.retrieve_relevant_chunks(message, 3)
                
                # Send sources
                sources_data = [
                    {
                        "document": s["metadata"]["document_name"],
                        "title": s["metadata"].get("title", "Content"),
                        "score": s["similarity_score"]
                    }
                    for s in sources.get("results", [])
                ]
                yield f"data: {json.dumps({'type': 'sources', 'sources': sources_data})}\n\n"
                
                # Generate answer
                yield f"data: {json.dumps({'type': 'status', 'message': 'Generating response...'})}\n\n"
                result = rag_system.answer_question(message, 3)
                answer = result.get("answer", "")
                
                # Stream tokens (word by word)
                words = answer.split()
                buffer = ""
                
                for i, word in enumerate(words):
                    buffer += word + " "
                    
                    # Send every 3 words
                    if (i + 1) % 3 == 0 or i == len(words) - 1:
                        yield f"data: {json.dumps({'type': 'token', 'content': buffer.strip()})}\n\n"
                        buffer = ""
                        await asyncio.sleep(0.03)  # Small delay for streaming effect
                
                # Update context
                topics = extract_topics_from_query(message)
                for topic in topics:
                    context.add_current_topic(topic)
                
                new_token = await create_session_token(context)
                
                # Send completion
                completion_data = {
                    "type": "complete",
                    "metadata": {
                        "new_session_token": new_token,
                        "agent": "tutor",
                        "topics": context.current_topics
                    }
                }
                yield f"data: {json.dumps(completion_data)}\n\n"
                
            else:
                # Non-streaming for other intents
                response = await coordinator.handle_conversation(message, context)
                new_token = await create_session_token(context)
                
                completion_data = {
                    "type": "complete",
                    "content": response,
                    "metadata": {
                        "new_session_token": new_token,
                        "agent": "coordinator",
                        "intent": intent.intent_type
                    }
                }
                yield f"data: {json.dumps(completion_data)}\n\n"
                
        except Exception as e:
            logger.error(f"Stream error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )


@router.get("/history", response_model=ChatHistoryResponse)
async def get_chat_history(context: MedicalContext = Depends(get_current_session)):
    """
    Get conversation history for current session.
    
    Returns all interactions in the current session with timestamps.
    """
    history = context.session_history
    
    interactions = []
    for i, msg in enumerate(history.user_messages):
        interactions.append({
            "timestamp": msg.get("timestamp", ""),
            "user_message": msg.get("message", ""),
            "agent_response": history.agent_responses[i] if i < len(history.agent_responses) else None,
            "topics": msg.get("topics", [])
        })
    
    new_token = await create_session_token(context)
    
    return ChatHistoryResponse(
        session_id=history.session_id,
        interactions=interactions,
        topics_covered=history.topics_covered,
        new_session_token=new_token
    )


async def handle_explanation(message: str, context: MedicalContext) -> dict:
    """Handle explanation intent using RAG."""
    rag_system = context.rag_system
    result = rag_system.answer_question(message, 3)
    
    return {
        "response": result.get("answer", ""),
        "sources": result.get("sources", [])
    }


