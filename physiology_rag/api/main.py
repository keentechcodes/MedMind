"""
Main FastAPI application for MedMind API.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from physiology_rag.config.settings import get_settings
from physiology_rag.core.rag_system import RAGSystem
from physiology_rag.utils.logging import get_logger

# Import routers
from physiology_rag.api.routers import auth, chat, query, documents
from physiology_rag.api.models import HealthResponse, RootResponse

logger = get_logger("api_main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Initializes RAG system on startup and handles cleanup.
    """
    logger.info("Starting up MedMind API...")
    
    try:
        # Initialize RAG system
        settings = get_settings()
        app.state.rag_system = RAGSystem(settings.gemini_api_key)
        logger.info("RAG system initialized successfully")
        
        # Initialize cache
        app.state.cache = {}
        
    except Exception as e:
        logger.error(f"Failed to initialize RAG system: {e}")
        app.state.rag_system = None
    
    yield
    
    # Cleanup on shutdown
    logger.info("Shutting down MedMind API...")
    # Add any cleanup code here (close DB connections, etc.)


# Create FastAPI app
app = FastAPI(
    title="MedMind API",
    description="AI-powered medical education API with multi-agent RAG system",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# CORS configuration
# Note: When allow_origins=["*"], allow_credentials must be False for browser security
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure specific origins for production
    allow_credentials=False,  # Must be False when using wildcard origins
    allow_methods=["*"],
    allow_headers=["*"],
)

# TODO: Add rate limiting for production
# Consider using slowapi or fastapi-limiter with Redis to prevent abuse
# Example:
# from slowapi import Limiter
# limiter = Limiter(key_func=get_remote_address)
# app.state.limiter = limiter
# app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Health check endpoint
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.
    
    Returns API status and RAG system initialization status.
    """
    rag_status = "initialized" if hasattr(app.state, 'rag_system') and app.state.rag_system else "not_initialized"
    
    return HealthResponse(
        status="healthy",
        rag_system=rag_status,
        version="1.0.0"
    )


# Root endpoint
@app.get("/", response_model=RootResponse)
async def root():
    """
    Root endpoint with API information.
    
    Returns API metadata and available endpoints.
    """
    return RootResponse(
        name="MedMind API",
        version="1.0.0",
        endpoints={
            "auth": "/auth",
            "chat": "/chat",
            "query": "/query",
            "documents": "/documents"
        },
        docs="/docs"
    )


# Include routers
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(query.router)
app.include_router(documents.router)


# Error handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "type": "internal_error"}
    )


if __name__ == "__main__":
    import uvicorn
    
    settings = get_settings()
    
    uvicorn.run(
        "physiology_rag.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
