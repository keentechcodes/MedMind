"""
Coordinator Agent - Main orchestrator for MedMind's multi-agent learning system.
Routes educational requests to specialized agents and coordinates responses.
"""

import re
from typing import Any, Dict, List, Optional
from datetime import datetime

from pydantic_ai import Agent, RunContext
from pydantic import BaseModel

from physiology_rag.dependencies.medical_context import MedicalContext, create_medical_context
from physiology_rag.models.learning_models import (
    LearningResponse, 
    LearningIntent, 
    UserQuery,
    QuizResponse,
    TutorResponse,
    ProgressUpdate,
)
from physiology_rag.core.rag_system import RAGSystem
from physiology_rag.utils.logging import get_logger

logger = get_logger("coordinator_agent")


class CoordinatorAgent:
    """
    Main orchestrator agent that routes requests to specialized learning agents.
    Provides the primary interface for student interactions with MedMind.
    """
    
    def __init__(self, model_name: str = "gemini-2.0-flash-exp"):
        """
        Initialize the Coordinator Agent.
        
        Args:
            model_name: The AI model to use for coordination decisions
        """
        self.model_name = model_name
        
        # Create the PydanticAI agent for coordination
        self.agent = Agent(
            model_name,
            deps_type=MedicalContext,
            output_type=LearningResponse,
            system_prompt=self._get_system_prompt()
        )
        
        # Register tools for agent coordination
        self._register_tools()
        
        logger.info(f"Initialized CoordinatorAgent with model: {model_name}")
    
    def _get_system_prompt(self) -> str:
        """Define the coordinator agent's system prompt."""
        return """
You are the Coordinator Agent for MedMind, an AI-powered medical education platform.

When a student asks a question, you should:

1. If they want explanations or ask medical questions:
   - Use the get_detailed_explanation tool to provide educational content
   
2. If they want quizzes or practice questions:
   - Use the generate_basic_quiz tool to create questions
   
3. If they ask about their progress:
   - Use the check_learning_progress tool to show their learning status
   
4. For general medical information searches:
   - Use the search_medical_content tool to find relevant documents

Always use the appropriate tools to provide educational responses. You have access to medical physiology documents through these tools.
"""
    
    def _register_tools(self) -> None:
        """Register tools for the coordinator agent."""
        
        @self.agent.tool
        async def search_medical_content(
            ctx: RunContext[MedicalContext], 
            query: str, 
            max_results: int = 3
        ) -> Dict[str, Any]:
            """Search medical documents using the RAG system."""
            logger.info(f"Searching medical content for: {query}")
            
            try:
                results = ctx.deps.rag_system.retrieve_relevant_chunks(query, max_results)
                
                # Track the topic in session context
                if results.get('results'):
                    topics = self._extract_topics_from_query(query)
                    for topic in topics:
                        ctx.deps.add_current_topic(topic)
                
                return {
                    "success": True,
                    "results": results.get('results', []),
                    "query": query,
                    "sources_found": len(results.get('results', []))
                }
            except Exception as e:
                logger.error(f"Error searching medical content: {e}")
                return {
                    "success": False,
                    "error": str(e),
                    "query": query
                }
        
        @self.agent.tool
        async def generate_basic_quiz(
            ctx: RunContext[MedicalContext],
            topic: str,
            difficulty: str = "intermediate",
            question_count: int = 3
        ) -> Dict[str, Any]:
            """Generate a basic quiz using RAG content (placeholder for Quiz Agent)."""
            logger.info(f"Generating basic quiz on {topic} with {question_count} questions")
            
            try:
                # Search for relevant content
                search_results = ctx.deps.rag_system.retrieve_relevant_chunks(
                    f"quiz questions about {topic}", question_count
                )
                
                # For now, create a simple placeholder response
                # This will be replaced by actual Quiz Agent delegation
                quiz_data = {
                    "topic": topic,
                    "difficulty": difficulty,
                    "question_count": question_count,
                    "sources_used": len(search_results.get('results', [])),
                    "placeholder": True,
                    "message": f"Generated {question_count} {difficulty} questions about {topic}"
                }
                
                # Update learning context
                ctx.deps.add_current_topic(topic)
                ctx.deps.add_learning_objective(f"Practice {topic} concepts at {difficulty} level")
                
                return quiz_data
                
            except Exception as e:
                logger.error(f"Error generating quiz: {e}")
                return {"error": str(e), "topic": topic}
        
        @self.agent.tool
        async def get_detailed_explanation(
            ctx: RunContext[MedicalContext],
            question: str,
            complexity_level: str = "intermediate"
        ) -> Dict[str, Any]:
            """Provide detailed medical explanation (placeholder for Tutor Agent)."""
            logger.info(f"Generating explanation for: {question}")
            
            try:
                # Use RAG system to generate complete response
                explanation_query = f"explain {question} in detail"
                full_response = ctx.deps.rag_system.answer_question(explanation_query, 3)
                
                if full_response.get('answer') and not full_response.get('error'):
                    explanation_data = {
                        "question": question,
                        "explanation": full_response['answer'],
                        "sources": [r['metadata']['document_name'] for r in full_response.get('sources', [])],
                        "complexity_level": complexity_level,
                        "confidence": 0.85  # Placeholder confidence score
                    }
                else:
                    explanation_data = {
                        "question": question,
                        "explanation": full_response.get('answer', "I don't have enough information to provide a detailed explanation."),
                        "sources": [],
                        "complexity_level": complexity_level,
                        "confidence": 0.0
                    }
                
                # Extract and track topics
                topics = self._extract_topics_from_query(question)
                for topic in topics:
                    ctx.deps.add_current_topic(topic)
                
                return explanation_data
                
            except Exception as e:
                logger.error(f"Error generating explanation: {e}")
                return {"error": str(e), "question": question}
        
        @self.agent.tool
        async def check_learning_progress(
            ctx: RunContext[MedicalContext]
        ) -> Dict[str, Any]:
            """Check current learning progress (placeholder for Progress Agent)."""
            logger.info(f"Checking progress for user: {ctx.deps.user_id}")
            
            try:
                profile = ctx.deps.learning_profile
                context_summary = ctx.deps.get_context_summary()
                
                progress_data = {
                    "user_id": ctx.deps.user_id,
                    "overall_accuracy": profile.overall_accuracy,
                    "mastery_scores": profile.mastery_scores,
                    "knowledge_gaps": profile.knowledge_gaps,
                    "learning_streak": profile.learning_streak,
                    "session_topics": ctx.deps.current_topics,
                    "total_sessions": profile.total_sessions,
                    "recommendations": self._generate_recommendations(ctx.deps)
                }
                
                return progress_data
                
            except Exception as e:
                logger.error(f"Error checking progress: {e}")
                return {"error": str(e)}
    
    def _extract_topics_from_query(self, query: str) -> List[str]:
        """Extract medical topics from user query."""
        # Simple topic extraction - can be enhanced with NLP
        medical_terms = [
            "neurophysiology", "cardiovascular", "respiratory", "endocrine",
            "musculoskeletal", "digestive", "renal", "immune", "reproduction",
            "metabolism", "homeostasis", "synapse", "neuron", "hormone",
            "blood", "heart", "lung", "kidney", "muscle", "bone"
        ]
        
        topics = []
        query_lower = query.lower()
        
        for term in medical_terms:
            if term in query_lower:
                topics.append(term)
        
        return topics
    
    def _generate_recommendations(self, context: MedicalContext) -> List[str]:
        """Generate learning recommendations based on context."""
        recommendations = []
        
        # Knowledge gaps recommendations
        if context.learning_profile.knowledge_gaps:
            recommendations.append(
                f"Review {len(context.learning_profile.knowledge_gaps)} topics that need attention"
            )
        
        # Difficulty progression
        for topic, score in context.learning_profile.mastery_scores.items():
            if score > 0.8:
                recommendations.append(f"Ready for advanced {topic} concepts")
            elif score < 0.4:
                recommendations.append(f"Practice basic {topic} fundamentals")
        
        # Session continuity
        if context.current_topics:
            recommendations.append(f"Continue exploring {', '.join(context.current_topics)}")
        
        return recommendations[:3]  # Limit to top 3 recommendations
    
    def _parse_learning_intent(self, user_input: str, context: MedicalContext) -> LearningIntent:
        """Parse user input to determine learning intent."""
        input_lower = user_input.lower()
        
        # Quiz intent patterns
        quiz_patterns = ["quiz", "test", "question", "practice", "assessment"]
        if any(pattern in input_lower for pattern in quiz_patterns):
            return LearningIntent(
                intent_type="quiz",
                topic=self._extract_primary_topic(user_input),
                difficulty=context.preferences.preferred_difficulty,
                specific_request=user_input
            )
        
        # Explanation intent patterns
        explain_patterns = ["explain", "what is", "how does", "why", "definition", "describe"]
        if any(pattern in input_lower for pattern in explain_patterns):
            return LearningIntent(
                intent_type="explanation",
                topic=self._extract_primary_topic(user_input),
                specific_request=user_input
            )
        
        # Progress intent patterns
        progress_patterns = ["progress", "how am i doing", "stats", "performance", "mastery"]
        if any(pattern in input_lower for pattern in progress_patterns):
            return LearningIntent(
                intent_type="progress",
                specific_request=user_input
            )
        
        # Default to general conversation
        return LearningIntent(
            intent_type="general",
            topic=self._extract_primary_topic(user_input),
            specific_request=user_input
        )
    
    def _extract_primary_topic(self, text: str) -> Optional[str]:
        """Extract the primary medical topic from text."""
        topics = self._extract_topics_from_query(text)
        return topics[0] if topics else None
    
    async def process_user_input(
        self, 
        user_input: str, 
        context: MedicalContext
    ) -> LearningResponse:
        """
        Process user input and coordinate appropriate agent response.
        
        Args:
            user_input: Student's question or request
            context: Current medical learning context
            
        Returns:
            Coordinated learning response
        """
        logger.info(f"Processing user input: {user_input[:100]}...")
        
        try:
            # Parse learning intent
            intent = self._parse_learning_intent(user_input, context)
            
            # Run the coordinator agent
            result = await self.agent.run(
                user_input,
                deps=context
            )
            
            # Update session history
            context.session_history.add_interaction(
                user_input,
                {"agent": "coordinator", "response": result.data.dict()},
                context.current_topics
            )
            
            return result.data
            
        except Exception as e:
            logger.error(f"Error processing user input: {e}")
            
            # Return error response
            return LearningResponse(
                intent=LearningIntent(intent_type="general", specific_request=user_input),
                content_type="conversation",
                content={"error": str(e)},
                agent_used="coordinator",
                conversation_text=f"I encountered an error processing your request: {e}"
            )
    
    async def handle_conversation(
        self,
        message: str,
        context: MedicalContext
    ) -> str:
        """
        Handle a conversational message and return a text response.
        
        Args:
            message: User's message
            context: Medical learning context
            
        Returns:
            Text response for conversation
        """
        try:
            # Simplified approach - directly use RAG system for now
            if "quiz" in message.lower():
                # Extract topic and generate simple quiz response
                topics = self._extract_topics_from_query(message)
                topic = topics[0] if topics else "general physiology"
                return f"I'd create a quiz about {topic}, but the Quiz Agent is still being implemented. For now, try asking me to explain a specific topic!"
            
            elif "progress" in message.lower():
                return f"Your current learning progress: You've covered {len(context.current_topics)} topics in this session. The Progress Agent is being developed for detailed analytics."
            
            else:
                # Use RAG system directly for explanations
                try:
                    rag_response = context.rag_system.answer_question(message, 3)
                    if rag_response.get('answer') and not rag_response.get('error'):
                        return rag_response['answer']
                    else:
                        return "I couldn't find specific information about that topic in the medical documents. Could you try asking about neurophysiology, motor control, or other physiology topics?"
                except Exception as rag_error:
                    logger.error(f"RAG system error: {rag_error}")
                    return f"I'm having trouble accessing the medical documents right now. Error: {rag_error}"
                
        except Exception as e:
            logger.error(f"Error handling conversation: {e}")
            return f"I'm sorry, I encountered an error: {e}"


def create_coordinator_agent(
    rag_system: RAGSystem,
    user_id: str = "default_user",
    model_name: str = "gemini-2.0-flash-exp"
) -> tuple[CoordinatorAgent, MedicalContext]:
    """
    Factory function to create a Coordinator Agent with medical context.
    
    Args:
        rag_system: Initialized RAG system for document retrieval
        user_id: Unique identifier for the user
        model_name: AI model to use for coordination
        
    Returns:
        Tuple of (CoordinatorAgent, MedicalContext)
    """
    # Create coordinator agent
    coordinator = CoordinatorAgent(model_name)
    
    # Create medical context
    context = create_medical_context(
        user_id=user_id,
        rag_system=rag_system
    )
    
    logger.info(f"Created coordinator agent for user: {user_id}")
    
    return coordinator, context


# CLI entry point for testing
async def main():
    """Main entry point for testing the coordinator agent."""
    from physiology_rag.config.settings import get_settings
    
    # Initialize RAG system
    settings = get_settings()
    rag_system = RAGSystem(settings.gemini_api_key)
    
    # Create coordinator
    coordinator, context = create_coordinator_agent(rag_system, "test_user")
    
    # Test conversation
    test_messages = [
        "Explain how synaptic transmission works",
        "Can you quiz me on neurophysiology?",
        "How am I doing with my learning progress?"
    ]
    
    for message in test_messages:
        print(f"\nUser: {message}")
        response = await coordinator.handle_conversation(message, context)
        print(f"MedMind: {response}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())