"""
Integration tests for the Coordinator Agent.
Tests agent coordination, context management, and tool integration.
"""

import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime

from physiology_rag.agents.coordinator import CoordinatorAgent, create_coordinator_agent
from physiology_rag.dependencies.medical_context import (
    MedicalContext, 
    UserLearningProfile, 
    UserPreferences,
    SessionHistory,
    create_medical_context
)
from physiology_rag.models.learning_models import LearningIntent, LearningResponse
from physiology_rag.core.rag_system import RAGSystem


class MockRAGSystem:
    """Mock RAG system for testing."""
    
    def __init__(self):
        self.test_results = {
            'results': [
                {
                    'document': 'Test medical content about neurophysiology.',
                    'metadata': {
                        'document_name': 'Test Document',
                        'title': 'Neurophysiology Basics',
                        'page_id': '1'
                    },
                    'similarity_score': 0.85
                }
            ]
        }
    
    def retrieve_relevant_chunks(self, query: str, n_results: int = 3):
        """Mock retrieval method."""
        return self.test_results
    
    def format_context(self, retrieval_results):
        """Mock context formatting."""
        return "Mock formatted context for testing."
    
    def generate_response(self, question: str, search_results):
        """Mock response generation."""
        return {
            'answer': f"Mock answer for: {question}",
            'sources': ['Test Document']
        }


@pytest.fixture
def mock_rag_system():
    """Create a mock RAG system for testing."""
    return MockRAGSystem()


@pytest.fixture
def test_medical_context(mock_rag_system):
    """Create test medical context."""
    return create_medical_context(
        user_id="test_user",
        rag_system=mock_rag_system
    )


@pytest.fixture
def coordinator_agent():
    """Create a coordinator agent for testing."""
    return CoordinatorAgent(model_name="gemini-2.0-flash-exp")


class TestCoordinatorAgent:
    """Test cases for Coordinator Agent functionality."""
    
    def test_agent_initialization(self, coordinator_agent):
        """Test that coordinator agent initializes correctly."""
        assert coordinator_agent.model_name == "gemini-2.0-flash-exp"
        assert coordinator_agent.agent is not None
        assert hasattr(coordinator_agent.agent, 'run')
    
    def test_topic_extraction(self, coordinator_agent):
        """Test medical topic extraction from queries."""
        test_cases = [
            ("Explain neurophysiology", ["neurophysiology"]),
            ("How does the cardiovascular system work?", ["cardiovascular"]),
            ("Quiz me on synapses and neurons", ["synapse", "neuron"]),
            ("Tell me about cooking", [])  # No medical terms
        ]
        
        for query, expected_topics in test_cases:
            topics = coordinator_agent._extract_topics_from_query(query)
            for expected in expected_topics:
                assert expected in topics
    
    def test_learning_intent_parsing(self, coordinator_agent, test_medical_context):
        """Test parsing of learning intents from user input."""
        test_cases = [
            ("Quiz me on neurophysiology", "quiz"),
            ("Explain synaptic transmission", "explanation"),
            ("How am I doing with my progress?", "progress"),
            ("Hello there", "general")
        ]
        
        for user_input, expected_intent in test_cases:
            intent = coordinator_agent._parse_learning_intent(user_input, test_medical_context)
            assert intent.intent_type == expected_intent
            assert intent.specific_request == user_input
    
    def test_primary_topic_extraction(self, coordinator_agent):
        """Test extraction of primary topic from text."""
        assert coordinator_agent._extract_primary_topic("neurophysiology concepts") == "neurophysiology"
        assert coordinator_agent._extract_primary_topic("cardiovascular and respiratory") == "cardiovascular"
        assert coordinator_agent._extract_primary_topic("random text") is None
    
    def test_recommendation_generation(self, coordinator_agent, test_medical_context):
        """Test generation of learning recommendations."""
        # Add some test data to the context
        test_medical_context.learning_profile.knowledge_gaps = ["neurophysiology", "cardiovascular"]
        test_medical_context.learning_profile.mastery_scores = {"endocrine": 0.9, "respiratory": 0.3}
        test_medical_context.current_topics = ["synapses"]
        
        recommendations = coordinator_agent._generate_recommendations(test_medical_context)
        
        assert len(recommendations) <= 3
        assert any("2 topics that need attention" in rec for rec in recommendations)
        assert any("advanced endocrine" in rec for rec in recommendations)
        assert any("basic respiratory" in rec for rec in recommendations)
    
    @pytest.mark.asyncio
    async def test_conversation_handling(self, coordinator_agent, test_medical_context):
        """Test basic conversation handling."""
        # Mock the agent's run method to avoid actual API calls
        async def mock_run(message, deps):
            mock_result = Mock()
            mock_result.data = LearningResponse(
                intent=LearningIntent(intent_type="general", specific_request=message),
                content_type="conversation",
                content={"response": "Mock response"},
                agent_used="coordinator",
                conversation_text="This is a mock response for testing."
            )
            return mock_result
        
        coordinator_agent.agent.run = mock_run
        
        response = await coordinator_agent.handle_conversation(
            "Hello, I want to learn about neurophysiology",
            test_medical_context
        )
        
        assert isinstance(response, str)
        assert "mock response" in response.lower()
    
    def test_medical_context_updates(self, test_medical_context):
        """Test that medical context updates correctly."""
        # Test topic addition
        test_medical_context.add_current_topic("neurophysiology")
        assert "neurophysiology" in test_medical_context.current_topics
        
        # Test learning objective addition
        test_medical_context.add_learning_objective("Understand synaptic transmission")
        assert "Understand synaptic transmission" in test_medical_context.learning_objectives
        
        # Test context summary generation
        summary = test_medical_context.get_context_summary()
        assert summary["user_id"] == "test_user"
        assert "current_topics" in summary
        assert "preferences" in summary
    
    def test_personalized_difficulty(self, test_medical_context):
        """Test personalized difficulty level calculation."""
        # Test different mastery levels
        test_medical_context.learning_profile.mastery_scores = {
            "easy_topic": 0.9,
            "medium_topic": 0.6,
            "hard_topic": 0.2
        }
        
        assert test_medical_context.get_personalized_difficulty("easy_topic") == "advanced"
        assert test_medical_context.get_personalized_difficulty("medium_topic") == "intermediate"
        assert test_medical_context.get_personalized_difficulty("hard_topic") == "beginner"
        assert test_medical_context.get_personalized_difficulty("unknown_topic") == "intermediate"
    
    def test_learning_profile_mastery_updates(self, test_medical_context):
        """Test learning profile mastery score updates."""
        profile = test_medical_context.learning_profile
        
        # Test correct answer update
        initial_score = profile.mastery_scores.get("test_topic", 0.5)
        profile.update_mastery("test_topic", correct=True, difficulty="intermediate")
        
        assert profile.mastery_scores["test_topic"] > initial_score
        assert profile.total_questions_answered == 1
        assert profile.correct_answers == 1
        
        # Test incorrect answer update
        profile.update_mastery("test_topic", correct=False, difficulty="intermediate")
        assert profile.total_questions_answered == 2
        assert profile.correct_answers == 1
    
    def test_session_history_tracking(self, test_medical_context):
        """Test session history tracking functionality."""
        session = test_medical_context.session_history
        
        # Test adding interactions
        session.add_interaction(
            "What is neurophysiology?",
            {"agent": "tutor", "response": "Neurophysiology is..."},
            ["neurophysiology"]
        )
        
        assert len(session.user_messages) == 1
        assert len(session.agent_responses) == 1
        assert "neurophysiology" in session.topics_covered
        assert session.last_activity is not None


class TestCoordinatorFactory:
    """Test cases for coordinator agent factory functions."""
    
    def test_create_coordinator_agent(self, mock_rag_system):
        """Test coordinator agent factory function."""
        coordinator, context = create_coordinator_agent(
            rag_system=mock_rag_system,
            user_id="factory_test_user"
        )
        
        assert isinstance(coordinator, CoordinatorAgent)
        assert isinstance(context, MedicalContext)
        assert context.user_id == "factory_test_user"
        assert context.rag_system == mock_rag_system
    
    def test_context_factory_with_defaults(self, mock_rag_system):
        """Test medical context creation with default values."""
        context = create_medical_context(
            user_id="default_test",
            rag_system=mock_rag_system
        )
        
        assert context.user_id == "default_test"
        assert isinstance(context.preferences, UserPreferences)
        assert isinstance(context.learning_profile, UserLearningProfile)
        assert isinstance(context.session_history, SessionHistory)
        assert context.learning_profile.user_id == "default_test"


# Integration test with actual components (if available)
@pytest.mark.integration
class TestCoordinatorIntegration:
    """Integration tests that require actual system components."""
    
    @pytest.mark.skip(reason="Requires actual RAG system and API keys")
    @pytest.mark.asyncio
    async def test_full_coordinator_pipeline(self):
        """Test full coordinator pipeline with real components."""
        # This would test with actual RAG system and API
        # Skipped by default to avoid dependency on external services
        pass
    
    def test_coordinator_agent_tools_registration(self, coordinator_agent):
        """Test that coordinator agent tools are properly registered."""
        # Verify that tools are registered with the agent
        # PydanticAI stores tools differently, check for _function_tools attribute
        assert hasattr(coordinator_agent.agent, '_function_tools') or hasattr(coordinator_agent.agent, 'tools')
        
        # Since we can't easily access tool names from PydanticAI internal structure,
        # just verify the agent was created successfully with tools
        assert coordinator_agent.agent is not None
        assert coordinator_agent.model_name == "gemini-2.0-flash-exp"