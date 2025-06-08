"""Shared dependencies and context for PydanticAI agents."""

from .medical_context import MedicalContext, UserLearningProfile, UserPreferences

__all__ = [
    "MedicalContext",
    "UserLearningProfile", 
    "UserPreferences",
]