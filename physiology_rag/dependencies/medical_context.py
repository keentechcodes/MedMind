"""
Shared medical context and user profiles for PydanticAI agents.
Provides dependency injection for coordinated learning experiences.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any

from physiology_rag.core.rag_system import RAGSystem


@dataclass
class UserPreferences:
    """User learning preferences and settings."""
    preferred_difficulty: str = "intermediate"  # beginner, intermediate, advanced
    quiz_length: int = 5
    explanation_style: str = "detailed"  # brief, detailed, comprehensive
    spaced_repetition_enabled: bool = True
    visual_learning_mode: bool = False
    interaction_style: str = "conversational"  # formal, conversational, concise


@dataclass
class UserLearningProfile:
    """User learning analytics and progress tracking."""
    user_id: str
    mastery_scores: Dict[str, float] = field(default_factory=dict)  # topic -> score (0-1)
    difficulty_preferences: Dict[str, str] = field(default_factory=dict)  # topic -> level
    spaced_repetition_schedule: Dict[str, datetime] = field(default_factory=dict)  # topic -> next_review
    knowledge_gaps: List[str] = field(default_factory=list)  # topics needing review
    learning_streak: int = 0
    total_sessions: int = 0
    correct_answers: int = 0
    total_questions_answered: int = 0
    
    @property
    def overall_accuracy(self) -> float:
        """Calculate overall accuracy percentage."""
        if self.total_questions_answered == 0:
            return 0.0
        return self.correct_answers / self.total_questions_answered
    
    def update_mastery(self, topic: str, correct: bool, difficulty: str = "intermediate") -> None:
        """Update mastery score for a topic based on performance."""
        # Weight based on difficulty
        difficulty_weights = {"beginner": 0.5, "intermediate": 1.0, "advanced": 1.5}
        weight = difficulty_weights.get(difficulty, 1.0)
        
        # Calculate score change
        score_change = weight * 0.1 if correct else -weight * 0.05
        
        # Update mastery score
        current_score = self.mastery_scores.get(topic, 0.5)
        new_score = max(0.0, min(1.0, current_score + score_change))
        self.mastery_scores[topic] = new_score
        
        # Update counters
        self.total_questions_answered += 1
        if correct:
            self.correct_answers += 1
        
        # Update knowledge gaps
        if new_score < 0.6 and topic not in self.knowledge_gaps:
            self.knowledge_gaps.append(topic)
        elif new_score >= 0.7 and topic in self.knowledge_gaps:
            self.knowledge_gaps.remove(topic)


@dataclass
class SessionHistory:
    """Track conversation and learning session history."""
    session_id: str
    user_messages: List[Dict[str, Any]] = field(default_factory=list)
    agent_responses: List[Dict[str, Any]] = field(default_factory=list)
    topics_covered: List[str] = field(default_factory=list)
    questions_generated: List[Dict[str, Any]] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    
    def add_interaction(self, user_message: str, agent_response: Dict[str, Any], topics: List[str] = None) -> None:
        """Add a user-agent interaction to the session."""
        self.user_messages.append({
            "timestamp": datetime.now(),
            "message": user_message,
            "topics": topics or []
        })
        
        self.agent_responses.append({
            "timestamp": datetime.now(),
            **agent_response
        })
        
        if topics:
            for topic in topics:
                if topic not in self.topics_covered:
                    self.topics_covered.append(topic)
        
        self.last_activity = datetime.now()


@dataclass
class MedicalContext:
    """
    Shared context across all medical education agents.
    Provides dependency injection for coordinated learning experiences.
    """
    user_id: str
    rag_system: RAGSystem
    learning_profile: UserLearningProfile
    preferences: UserPreferences
    session_history: SessionHistory
    current_topics: List[str] = field(default_factory=list)
    learning_objectives: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Initialize additional context after creation."""
        # Ensure learning profile has correct user_id
        if self.learning_profile.user_id != self.user_id:
            self.learning_profile.user_id = self.user_id
    
    def get_context_summary(self) -> Dict[str, Any]:
        """Get a summary of current learning context for agents."""
        return {
            "user_id": self.user_id,
            "current_topics": self.current_topics,
            "learning_objectives": self.learning_objectives,
            "mastery_scores": self.learning_profile.mastery_scores,
            "knowledge_gaps": self.learning_profile.knowledge_gaps,
            "preferences": {
                "difficulty": self.preferences.preferred_difficulty,
                "style": self.preferences.explanation_style,
                "quiz_length": self.preferences.quiz_length
            },
            "session_stats": {
                "topics_covered": self.session_history.topics_covered,
                "interactions": len(self.session_history.user_messages),
                "accuracy": self.learning_profile.overall_accuracy
            }
        }
    
    def get_personalized_difficulty(self, topic: str) -> str:
        """Get personalized difficulty level for a topic based on mastery."""
        mastery = self.learning_profile.mastery_scores.get(topic, 0.5)
        
        if mastery < 0.4:
            return "beginner"
        elif mastery < 0.7:
            return "intermediate"
        else:
            return "advanced"
    
    def should_review_topic(self, topic: str) -> bool:
        """Check if a topic needs review based on spaced repetition."""
        if topic in self.learning_profile.knowledge_gaps:
            return True
        
        next_review = self.learning_profile.spaced_repetition_schedule.get(topic)
        if next_review and datetime.now() >= next_review:
            return True
        
        return False
    
    def add_learning_objective(self, objective: str) -> None:
        """Add a new learning objective for the session."""
        if objective not in self.learning_objectives:
            self.learning_objectives.append(objective)
    
    def add_current_topic(self, topic: str) -> None:
        """Add a topic to current focus."""
        if topic not in self.current_topics:
            self.current_topics.append(topic)


def create_medical_context(
    user_id: str,
    rag_system: RAGSystem,
    session_id: Optional[str] = None,
    preferences: Optional[UserPreferences] = None,
    learning_profile: Optional[UserLearningProfile] = None
) -> MedicalContext:
    """
    Factory function to create MedicalContext with defaults.
    
    Args:
        user_id: Unique identifier for the user
        rag_system: Initialized RAG system for document retrieval
        session_id: Optional session identifier
        preferences: Optional user preferences (creates defaults if None)
        learning_profile: Optional learning profile (creates new if None)
    
    Returns:
        Configured MedicalContext ready for agent use
    """
    # Create defaults if not provided
    if preferences is None:
        preferences = UserPreferences()
    
    if learning_profile is None:
        learning_profile = UserLearningProfile(user_id=user_id)
    
    session_id = session_id or f"{user_id}_{datetime.now().isoformat()}"
    session_history = SessionHistory(session_id=session_id)
    
    return MedicalContext(
        user_id=user_id,
        rag_system=rag_system,
        learning_profile=learning_profile,
        preferences=preferences,
        session_history=session_history
    )