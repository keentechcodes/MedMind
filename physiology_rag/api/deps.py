"""
Dependencies for the MedMind API.
Handles authentication, session management, and dependency injection.
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt

from physiology_rag.config.settings import get_settings
from physiology_rag.dependencies.medical_context import (
    MedicalContext,
    UserPreferences,
    UserLearningProfile,
    SessionHistory,
    create_medical_context,
)
from physiology_rag.core.rag_system import RAGSystem
from physiology_rag.utils.logging import get_logger

logger = get_logger("api_deps")
security = HTTPBearer(auto_error=False)


class SessionManager:
    """
    Manages user sessions using JWT tokens.
    Stores session state in JWT payload for stateless scaling.
    """
    
    def __init__(self):
        settings = get_settings()
        # Use dedicated JWT secret key, not the API key directly
        self.secret_key = settings.jwt_secret_key
        if not self.secret_key:
            raise ValueError("JWT secret key must be configured")
        self.algorithm = "HS256"
        self.access_token_expire_hours = 24
    
    def create_session_token(
        self,
        user_id: str,
        context_data: dict
    ) -> str:
        """
        Create a JWT token containing session state.
        
        Args:
            user_id: Unique user identifier
            context_data: Serialized MedicalContext state
            
        Returns:
            JWT token string
        """
        expire = datetime.utcnow() + timedelta(hours=self.access_token_expire_hours)
        
        payload = {
            "sub": user_id,
            "context": context_data,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access"
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return token
    
    def decode_session(self, token: str) -> dict:
        """
        Decode and validate a session token.
        
        Args:
            token: JWT token string
            
        Returns:
            Decoded payload
            
        Raises:
            HTTPException: If token is invalid or expired
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            
            if payload.get("type") != "access":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type"
                )
            
            return payload
            
        except JWTError as e:
            logger.warning(f"JWT decode error: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"}
            )
    
    def extract_context_from_payload(self, payload: dict) -> dict:
        """Extract context data from JWT payload."""
        return payload.get("context", {})


# Global session manager instance
session_manager = SessionManager()


async def get_rag_system(request=None) -> RAGSystem:
    """
    Dependency to get the initialized RAG system.
    Must be used within FastAPI request context.
    
    Args:
        request: Optional FastAPI request object to get app state from
    """
    from fastapi import Request
    
    # Try to get app from request context if provided
    if request is not None:
        app = request.app
    else:
        # Fallback: try to get from global registry if available
        # This avoids circular import
        from starlette.applications import Starlette
        from physiology_rag.api.main import app as main_app
        app = main_app
    
    if not hasattr(app.state, 'rag_system') or app.state.rag_system is None:
        logger.error("RAG system not initialized")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RAG system not available"
        )
    
    return app.state.rag_system


async def get_current_session(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> MedicalContext:
    """
    Dependency to get the current user's MedicalContext from session token.
    
    This restores the user's learning context, preferences, and history
    from the JWT token state.
    
    Args:
        credentials: Bearer token from Authorization header
        
    Returns:
        MedicalContext with user's session state
        
    Raises:
        HTTPException: If authentication fails
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    try:
        # Decode and validate token
        payload = session_manager.decode_session(credentials.credentials)
        user_id = payload.get("sub")
        context_data = session_manager.extract_context_from_payload(payload)
        
        # Get RAG system
        rag_system = await get_rag_system()
        
        # Restore or create user preferences
        preferences_data = context_data.get("preferences", {})
        preferences = UserPreferences(
            preferred_difficulty=preferences_data.get("difficulty", "intermediate"),
            explanation_style=preferences_data.get("style", "detailed"),
            quiz_length=preferences_data.get("quiz_length", 5)
        )
        
        # Restore or create learning profile
        profile_data = context_data.get("learning_profile", {})
        learning_profile = UserLearningProfile(
            user_id=user_id,
            mastery_scores=profile_data.get("mastery_scores", {}),
            knowledge_gaps=profile_data.get("knowledge_gaps", []),
            learning_streak=profile_data.get("learning_streak", 0),
            total_sessions=profile_data.get("total_sessions", 0),
            correct_answers=profile_data.get("correct_answers", 0),
            total_questions_answered=profile_data.get("total_questions_answered", 0)
        )
        
        # Restore session history if available
        session_data = context_data.get("session", {})
        session_history = SessionHistory(
            session_id=session_data.get("session_id", f"{user_id}_{datetime.now().isoformat()}"),
            topics_covered=session_data.get("topics_covered", [])
        )
        
        # Create medical context
        context = MedicalContext(
            user_id=user_id,
            rag_system=rag_system,
            learning_profile=learning_profile,
            preferences=preferences,
            session_history=session_history,
            current_topics=context_data.get("current_topics", []),
            learning_objectives=context_data.get("learning_objectives", [])
        )
        
        return context
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error restoring session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error restoring session"
        )


async def create_session_token(context: MedicalContext) -> str:
    """
    Create a new session token from current MedicalContext state.
    
    Args:
        context: Current medical context with updated state
        
    Returns:
        New JWT token
    """
    # Serialize context state
    context_data = {
        "current_topics": context.current_topics,
        "learning_objectives": context.learning_objectives,
        "preferences": {
            "difficulty": context.preferences.preferred_difficulty,
            "style": context.preferences.explanation_style,
            "quiz_length": context.preferences.quiz_length
        },
        "learning_profile": {
            "mastery_scores": context.learning_profile.mastery_scores,
            "knowledge_gaps": context.learning_profile.knowledge_gaps,
            "learning_streak": context.learning_profile.learning_streak,
            "total_sessions": context.learning_profile.total_sessions,
            "correct_answers": context.learning_profile.correct_answers,
            "total_questions_answered": context.learning_profile.total_questions_answered
        },
        "session": {
            "session_id": context.session_history.session_id,
            "topics_covered": context.session_history.topics_covered
        }
    }
    
    return session_manager.create_session_token(context.user_id, context_data)


async def get_optional_session(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[MedicalContext]:
    """
    Optional authentication - returns None if no token provided.
    Useful for endpoints that work with or without authentication.
    """
    if credentials is None:
        return None
    
    try:
        return await get_current_session(credentials)
    except HTTPException:
        return None


async def create_anonymous_session() -> tuple[MedicalContext, str]:
    """
    Create a new anonymous session.
    
    Returns:
        Tuple of (MedicalContext, session_token)
    """
    user_id = f"anon_{uuid.uuid4().hex[:8]}"
    rag_system = await get_rag_system()
    
    context = create_medical_context(user_id=user_id, rag_system=rag_system)
    token = await create_session_token(context)
    
    return context, token
