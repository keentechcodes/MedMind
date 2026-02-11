"""
MedMind API package.

This package provides a RESTful API for the MedMind medical education system.
It includes endpoints for chat, RAG queries, quizzes, progress tracking, and document management.
"""

from physiology_rag.api.main import app

__all__ = ["app"]
