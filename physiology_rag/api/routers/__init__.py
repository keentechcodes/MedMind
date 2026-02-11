"""
API routers package.
"""

from physiology_rag.api.routers.auth import router as auth_router
from physiology_rag.api.routers.chat import router as chat_router
from physiology_rag.api.routers.query import router as query_router
from physiology_rag.api.routers.documents import router as documents_router

__all__ = [
    "auth_router",
    "chat_router",
    "query_router",
    "documents_router",
]
