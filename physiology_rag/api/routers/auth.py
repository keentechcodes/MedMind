"""
Authentication router for MedMind API.
Handles session creation and management.
"""

from fastapi import APIRouter, Depends, HTTPException, status

from physiology_rag.api.models import LoginRequest, LoginResponse
from physiology_rag.api.deps import (
    create_anonymous_session,
    get_current_session,
    create_session_token
)
from physiology_rag.dependencies.medical_context import MedicalContext
from physiology_rag.utils.logging import get_logger

logger = get_logger("auth_router")
router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest = None):
    """
    Create a new session.
    
    If user_id is provided, creates a session for that user.
    If not provided, creates an anonymous session.
    
    Returns a JWT token that must be included in subsequent requests
    in the Authorization header as: Bearer <token>
    """
    try:
        # Create anonymous session if no user_id provided
        if request is None or request.user_id is None:
            context, token = await create_anonymous_session()
            user_id = context.user_id
            logger.info(f"Created anonymous session: {user_id}")
        else:
            # Create session for specific user
            from physiology_rag.dependencies.medical_context import create_medical_context
            from physiology_rag.api.deps import get_rag_system
            
            rag_system = await get_rag_system()
            context = create_medical_context(
                user_id=request.user_id,
                rag_system=rag_system
            )
            token = await create_session_token(context)
            user_id = request.user_id
            logger.info(f"Created session for user: {user_id}")
        
        return LoginResponse(
            access_token=token,
            token_type="bearer",
            user_id=user_id,
            expires_in=86400  # 24 hours
        )
        
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create session"
        )


@router.post("/refresh")
async def refresh_token(context: MedicalContext = Depends(get_current_session)):
    """
    Refresh the session token.
    
    Returns a new token with updated expiration time.
    Use this to keep the session alive.
    """
    try:
        new_token = await create_session_token(context)
        logger.info(f"Refreshed token for user: {context.user_id}")
        
        return {
            "access_token": new_token,
            "token_type": "bearer",
            "user_id": context.user_id,
            "expires_in": 86400
        }
        
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to refresh token"
        )


@router.get("/me")
async def get_current_user(context: MedicalContext = Depends(get_current_session)):
    """
    Get current user information from session.
    
    Returns user ID, preferences, and current session state.
    """
    return {
        "user_id": context.user_id,
        "preferences": {
            "difficulty": context.preferences.preferred_difficulty,
            "style": context.preferences.explanation_style,
            "quiz_length": context.preferences.quiz_length
        },
        "current_topics": context.current_topics,
        "learning_objectives": context.learning_objectives,
        "session_topics": context.session_history.topics_covered
    }
