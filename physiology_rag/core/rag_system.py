"""
RAG (Retrieval-Augmented Generation) system for the Physiology project.
Combines retrieval from ChromaDB with Gemini API for answer generation.
"""

from typing import Any, Dict, List

import google.generativeai as genai

from physiology_rag.config.settings import get_settings
from physiology_rag.utils.logging import get_logger
from physiology_rag.core.embeddings_service import EmbeddingsService

logger = get_logger("rag_system")


class RAGSystem:
    """
    Complete RAG system combining document retrieval with AI response generation.
    
    Provides context-aware answers to questions about physiology documents
    with source attribution and relevance scoring.
    """
    
    def __init__(self, api_key: str = None):
        """
        Initialize RAG system with Gemini API.
        
        Args:
            api_key: Gemini API key (defaults to settings)
        """
        settings = get_settings()
        
        # Configure API
        api_key = api_key or settings.gemini_api_key
        genai.configure(api_key=api_key)
        
        # Initialize embeddings service for retrieval
        self.embeddings_service = EmbeddingsService(api_key)
        
        # Initialize Gemini model for response generation
        self.model_name = settings.gemini_model_name
        self.model = genai.GenerativeModel(self.model_name)
        self.max_context_length = settings.max_context_length
        self.max_retrieval_results = settings.max_retrieval_results
        
        logger.info(f"Initialized RAGSystem with model: {self.model_name}")
        logger.info(f"Max context length: {self.max_context_length}")
        
    def retrieve_relevant_chunks(self, query: str, n_results: int = None) -> Dict[str, Any]:
        """
        Retrieve relevant document chunks for the query.
        
        Args:
            query: User question
            n_results: Number of results to retrieve (defaults to settings)
            
        Returns:
            Retrieval results with documents and metadata
        """
        n_results = n_results or self.max_retrieval_results
        logger.info(f"Retrieving relevant chunks for query: '{query}'")
        
        return self.embeddings_service.search_documents(query, n_results)
    
    def format_context(self, retrieval_results: Dict[str, Any]) -> str:
        """
        Format retrieved chunks into context for Gemini.
        
        Args:
            retrieval_results: Results from embeddings service
            
        Returns:
            Formatted context string
        """
        context_parts = []
        
        for i, result in enumerate(retrieval_results['results']):
            doc_name = result['metadata']['document_name']
            chunk_text = result['document']
            score = result['similarity_score']
            
            # Add section title if available
            section_title = result['metadata'].get('title', 'Content')
            page_id = result['metadata'].get('page_id', 'Unknown')
            
            context_part = f"""
Source {i+1}: {doc_name} - {section_title} (Page {page_id}) [Relevance: {score:.3f}]
{chunk_text}
---
"""
            context_parts.append(context_part)
        
        context = "\n".join(context_parts)
        
        # Limit context length to prevent timeouts
        if len(context) > self.max_context_length:
            context = context[:self.max_context_length]
            logger.info(f"Context truncated to {self.max_context_length} characters")
        
        logger.info(f"Formatted context with {len(retrieval_results['results'])} sources")
        return context
    
    def generate_answer(self, query: str, context: str) -> str:
        """
        Generate answer using Gemini with retrieved context.
        
        Args:
            query: User question
            context: Formatted context from retrieval
            
        Returns:
            Generated answer
        """
        prompt = f"""Based on this physiology information:

{context}

Question: {query}

Provide a clear, educational answer for medical students. Include source references when possible.
Focus on being accurate, comprehensive, and easy to understand."""

        try:
            logger.info("Generating response with Gemini")
            response = self.model.generate_content(prompt)
            
            if response.text:
                logger.info("Successfully generated response")
                return response.text
            else:
                logger.warning("Empty response from Gemini")
                return "I apologize, but I couldn't generate a proper response. Please try rephrasing your question."
                
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return f"Error generating response: {str(e)}"
    
    def answer_question(self, query: str, n_results: int = None) -> Dict[str, Any]:
        """
        Complete RAG pipeline: retrieve + generate answer.
        
        Args:
            query: User question
            n_results: Number of sources to retrieve (defaults to settings)
            
        Returns:
            Complete response with answer, sources, and metadata
        """
        logger.info(f"Processing question: '{query}'")
        
        try:
            # Step 1: Retrieve relevant chunks (limit to prevent long context)
            max_results = min(n_results or self.max_retrieval_results, 3)
            retrieval_results = self.retrieve_relevant_chunks(query, max_results)
            
            if not retrieval_results.get('results'):
                logger.warning("No relevant documents found")
                return {
                    'query': query,
                    'answer': "I couldn't find relevant information to answer your question. Please try rephrasing or asking about a different topic.",
                    'sources': [],
                    'context': "",
                    'error': "No relevant documents found"
                }
            
            # Step 2: Format context
            context = self.format_context(retrieval_results)
            
            # Step 3: Generate answer
            answer = self.generate_answer(query, context)
            
            result = {
                'query': query,
                'answer': answer,
                'sources': retrieval_results['results'],
                'context': context
            }
            
            logger.info("Successfully completed RAG pipeline")
            return result
            
        except Exception as e:
            logger.error(f"Error in RAG pipeline: {e}")
            return {
                'query': query,
                'answer': f"Error in RAG pipeline: {str(e)}",
                'sources': [],
                'context': "",
                'error': str(e)
            }
    
    def get_system_stats(self) -> Dict[str, Any]:
        """
        Get system statistics and health information.
        
        Returns:
            System statistics
        """
        try:
            embedding_stats = self.embeddings_service.get_collection_stats()
            return {
                'model_name': self.model_name,
                'max_context_length': self.max_context_length,
                'max_retrieval_results': self.max_retrieval_results,
                'vector_db_stats': embedding_stats
            }
        except Exception as e:
            logger.error(f"Error getting system stats: {e}")
            return {'error': str(e)}


def main():
    """CLI entry point for RAG system testing."""
    rag = RAGSystem()
    
    # Test questions
    test_questions = [
        "What is the cerebral cortex and what are its main functions?",
        "How does the blood-brain barrier work?", 
        "Explain the role of the hypothalamus in thermoregulation"
    ]
    
    # Show system stats
    stats = rag.get_system_stats()
    print("System Statistics:")
    print(f"  Model: {stats.get('model_name')}")
    print(f"  Vector DB: {stats.get('vector_db_stats', {}).get('total_chunks', 'Unknown')} chunks")
    print()
    
    for question in test_questions:
        print("=" * 80)
        print(f"QUESTION: {question}")
        print("=" * 80)
        
        result = rag.answer_question(question)
        
        print(f"\nANSWER:\n{result['answer']}")
        
        print(f"\nSOURCES USED:")
        for i, source in enumerate(result['sources']):
            doc_name = source['metadata']['document_name']
            title = source['metadata'].get('title', 'Content')
            score = source['similarity_score']
            print(f"{i+1}. {doc_name} - {title} (Score: {score:.3f})")
        
        print("\n")


if __name__ == "__main__":
    main()