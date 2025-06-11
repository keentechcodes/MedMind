#!/usr/bin/env python3
"""
MedMind - AI-Powered Medical Education Assistant
Multi-Agent Streamlit Interface with PydanticAI Integration
"""

import json
import asyncio
import streamlit as st
from pathlib import Path
from typing import Dict, Any, Optional

from physiology_rag.core.rag_system import RAGSystem
from physiology_rag.agents.coordinator import create_coordinator_agent
from physiology_rag.dependencies.medical_context import create_medical_context
from physiology_rag.models.learning_models import LearningResponse
from physiology_rag.config.settings import get_settings
from physiology_rag.utils.logging import get_logger

# Setup logging
logger = get_logger("streamlit_app")

# Get settings
settings = get_settings()

# Page config
st.set_page_config(
    page_title="MedMind - AI Medical Education",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)


@st.cache_resource
def init_agent_system():
    """Initialize Coordinator Agent system with caching."""
    try:
        logger.info("Initializing MedMind Agent System for Streamlit")
        
        # Check settings first
        settings = get_settings()
        logger.info(f"API key available: {bool(settings.gemini_api_key and settings.gemini_api_key != 'your-gemini-api-key-here')}")
        
        # Initialize RAG system
        rag_system = RAGSystem()
        logger.info(f"RAG system type: {type(rag_system)}")
        logger.info(f"RAG system methods: {[method for method in dir(rag_system) if not method.startswith('_')]}")
        
        # Verify the RAG system has the required methods
        if not hasattr(rag_system, 'answer_question'):
            raise AttributeError("RAGSystem does not have answer_question method")
        
        logger.info("RAG system initialized successfully")
        return rag_system
        
    except Exception as e:
        logger.error(f"Failed to initialize agent system: {e}")
        logger.error(f"Exception type: {type(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        st.error(f"Failed to initialize agent system: {e}")
        return None

def get_session_user_id() -> str:
    """Get or create a user ID for this session."""
    if "user_id" not in st.session_state:
        import uuid
        st.session_state.user_id = f"student_{str(uuid.uuid4())[:8]}"
    return st.session_state.user_id

def init_agent_for_session(rag_system: RAGSystem) -> tuple:
    """Initialize agent and context for this session."""
    try:
        user_id = get_session_user_id()
        
        # Create medical context for this user
        context = create_medical_context(rag_system, user_id)
        
        # Create coordinator agent
        coordinator, _ = create_coordinator_agent(rag_system, user_id)
        
        return coordinator, context
    except Exception as e:
        logger.error(f"Failed to initialize agent for session: {e}")
        raise e


def display_agent_response(response: LearningResponse):
    """Display agent response with appropriate formatting based on type."""
    
    # Display main content
    if hasattr(response, 'content') and response.content:
        st.markdown(response.content)
    
    # Handle different response types
    if response.content_type == "quiz":
        st.info("🎯 Quiz functionality coming soon! The agent detected you want to practice with questions.")
    elif response.content_type == "progress":
        st.info("📊 Progress tracking coming soon! The agent will show your learning analytics.")
    elif response.content_type == "explanation":
        # Standard explanation - content already displayed above
        pass
    
    # Display agent used
    if hasattr(response, 'agent_used'):
        st.caption(f"🤖 Handled by: {response.agent_used}")

def get_images_for_document(doc_name: str, max_images: int = 5) -> list:
    """Get images from a document with corrected paths."""
    try:
        settings = get_settings()
        processed_file = Path(settings.processed_data_dir) / "processed_documents.json"
        
        if not processed_file.exists():
            return []
        
        with open(processed_file, "r") as f:
            docs = json.load(f)
        
        # Find the document
        doc_data = None
        for doc in docs:
            if doc.get('document_name') == doc_name:
                doc_data = doc
                break
        
        if not doc_data or 'images' not in doc_data:
            return []
        
        # Return first few images with corrected paths
        images = []
        for img in doc_data['images'][:max_images]:
            # The correct path is data/processed/[doc_name]/[filename]
            correct_path = Path.cwd() / 'data' / 'processed' / doc_name / img['filename']
            
            # Also try some fallback paths just in case
            possible_paths = [
                correct_path,  # Most likely correct path
                Path(img['path']),  # Original stored path
                Path.cwd() / img['path'],  # Relative to current directory
                Path.cwd() / 'output' / doc_name / img['filename'],  # Alternative structure
            ]
            
            # Find working path
            working_path = None
            for path in possible_paths:
                if path.exists():
                    working_path = str(path)
                    break
            
            # Update image with working path
            if working_path:
                img_copy = img.copy()
                img_copy['working_path'] = working_path
                images.append(img_copy)
            else:
                # Keep original for debugging
                img_copy = img.copy()
                img_copy['attempted_path'] = str(correct_path)
                images.append(img_copy)
        
        return images
        
    except Exception as e:
        logger.error(f"Error getting images for document: {e}")
        return []

def display_sources(sources):
    """Display source information in a nice format with associated images."""
    if not sources:
        return
        
    st.subheader("📚 Sources")
    
    for i, source in enumerate(sources):
        score = source.get('similarity_score', 0.0)
        doc_name = source.get('metadata', {}).get('document_name', 'Unknown Document')
        
        with st.expander(f"Source {i+1}: {doc_name} (Score: {score:.3f})"):
            metadata = source.get('metadata', {})
            chunk_info = f"{metadata.get('chunk_index', '?')}/{metadata.get('total_chunks', '?')}"
            
            st.write("**Section:**", metadata.get('title', 'Content'))
            st.write("**Chunk:**", f"{metadata.get('chunk_index', '?')}/{metadata.get('total_chunks', '?')}")
            st.write("**Chunk Type:**", metadata.get('chunk_type', 'content'))
            
            # Display sample images from the document
            doc_images = get_images_for_document(doc_name, max_images=3)
            if doc_images:
                # Filter to only show images that were found
                found_images = [img for img in doc_images if 'working_path' in img]
                
                if found_images:
                    st.write(f"**Images from {doc_name}:** ({len(found_images)} found)")
                    
                    # Create columns for found images
                    if len(found_images) == 1:
                        img = found_images[0]
                        try:
                            st.image(
                                img['working_path'], 
                                caption=f"{img['type']} {img['number']} from {doc_name}",
                                width=400
                            )
                        except Exception as e:
                            st.write(f"Image: {img['filename']} (could not display: {e})")
                    
                    else:
                        # Show multiple images in columns
                        cols = st.columns(min(len(found_images), 3))  # Max 3 columns
                        for j, img in enumerate(found_images[:3]):  # Show max 3 images
                            try:
                                cols[j].image(
                                    img['working_path'], 
                                    caption=f"{img['type']} {img['number']}",
                                    width=200
                                )
                            except Exception as e:
                                cols[j].write(f"Image: {img['filename']} (error: {e})")
                
                else:
                    # No images found - show debug info
                    st.write(f"**Images from {doc_name}:** (0 found)")
                    if len(doc_images) > 0:
                        with st.expander("Debug: Image paths not found", expanded=False):
                            for img in doc_images:
                                st.write(f"• {img['filename']}")
                                if 'attempted_path' in img:
                                    st.caption(f"  Tried: {img['attempted_path']}")
                                st.caption(f"  Original: {img['path']}")
            
            st.write("**Content:**")
            st.write(source.get('document', 'No content available'))


def load_document_stats():
    """Load document statistics for the sidebar."""
    try:
        processed_file = Path(settings.processed_data_dir) / "processed_documents.json"
        
        if not processed_file.exists():
            return None, "Documents not processed yet. Run setup first."
        
        with open(processed_file, "r") as f:
            docs = json.load(f)
        
        return docs, None
        
    except Exception as e:
        logger.error(f"Error loading document stats: {e}")
        return None, f"Error loading documents: {e}"


def display_sidebar():
    """Display sidebar with document library and settings."""
    with st.sidebar:
        st.header("📖 Document Library")
        
        # Load and show document stats
        docs, error = load_document_stats()
        
        if error:
            st.error(error)
            if st.button("🔧 Run Setup"):
                st.info("Please run: `python scripts/setup.py` in your terminal")
            return None
        
        if docs:
            st.write(f"**Total Documents:** {len(docs)}")
            total_chunks = sum(doc.get('total_chunks', 0) for doc in docs)
            total_images = sum(doc.get('total_images', 0) for doc in docs)
            
            st.write(f"**Total Chunks:** {total_chunks}")
            st.write(f"**Total Images:** {total_images}")
            
            # Show documents in scrollable container
            st.write("**Documents:**")
            with st.container(height=300):
                for doc in docs:
                    doc_name = doc.get('document_name', 'Unknown')
                    chunks = doc.get('total_chunks', 0)
                    images = doc.get('total_images', 0)
                    with st.expander(f"📄 {doc_name}", expanded=False):
                        st.write(f"**Sections:** {chunks}")
                        st.write(f"**Images:** {images}")
                        
                        # Show file info if available
                        if 'file_path' in doc:
                            st.write(f"**Path:** {doc['file_path']}")
                        if 'processing_date' in doc:
                            st.write(f"**Processed:** {doc['processing_date']}")
        
        st.markdown("---")
        st.header("⚙️ Settings")
        
        # Settings controls
        num_sources = st.slider(
            "Number of sources to retrieve", 
            1, 10, 
            value=5,
            help="Adjust how many source documents to search through"
        )
        
        # Show system info
        st.markdown("---")
        st.header("🤖 Agent System")
        st.write("**Architecture:** Multi-Agent PydanticAI")
        st.write("**🔄 Status:** Temporary RAG-only mode")
        st.write("**🔍 Available:** Document Q&A with RAG")
        st.write("**🔄 Coming Soon:** Full Agent Integration")
        
        st.markdown("---")
        st.header("ℹ️ System Info")
        st.write(f"**Model:** {settings.gemini_model_name}")
        st.write(f"**Embedding Model:** {settings.gemini_embedding_model}")
        st.write(f"**Max Context:** {settings.max_context_length} chars")
        st.write(f"**User ID:** {get_session_user_id()}")
        
        return num_sources


def display_sample_questions():
    """Display sample questions when chat is empty."""
    st.markdown("### 💡 Try these learning modes:")
    
    # Learning mode examples
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**🧠 Ask for Explanations:**")
        explanation_questions = [
            "What is the cerebral cortex and what are its main functions?",
            "How does the blood-brain barrier work?",
            "Explain synaptic transmission",
            "What is the autonomic nervous system?"
        ]
        for i, question in enumerate(explanation_questions):
            if st.button(question, key=f"explain_{i}", use_container_width=True):
                return question
    
    with col2:
        st.markdown("**🎯 Try Agent Features:**")
        agent_questions = [
            "Quiz me on neurophysiology",
            "How am I doing with my progress?",
            "Test my knowledge of motor control",
            "What should I study next?"
        ]
        for i, question in enumerate(agent_questions):
            if st.button(question, key=f"agent_{i}", use_container_width=True):
                return question
    
    return None


def main():
    """Main Streamlit application."""
    # Title and description
    st.title("🧠 MedMind - AI Medical Education Assistant")
    st.markdown("""**AI-Powered Learning Platform**: Ask questions about physiology and get answers from medical documents. 
    Multi-agent architecture with PydanticAI coming soon for adaptive quizzes and progress tracking.""")
    
    # Check for API key
    if not settings.gemini_api_key or settings.gemini_api_key == "your-gemini-api-key-here":
        st.error("🔑 Gemini API key not configured!")
        st.markdown("""
        Please set your Gemini API key:
        1. Copy `.env.example` to `.env`
        2. Add your API key: `GEMINI_API_KEY=your-actual-key`
        3. Restart the Streamlit app
        """)
        return
    
    # Debug API key
    logger.info(f"Using API key: {settings.gemini_api_key[:10]}...")
    
    # Display sidebar and get settings
    num_sources = display_sidebar()
    if num_sources is None:
        return
    
    # Initialize Agent system
    rag_system = init_agent_system()
    if rag_system is None:
        st.error("Cannot proceed without agent system initialization")
        st.info("Please check your .env file and ensure GEMINI_API_KEY is set correctly")
        return
    
    # Validate RAG system type
    if not hasattr(rag_system, 'answer_question'):
        st.error(f"Invalid RAG system type: {type(rag_system)}")
        st.info("Expected RAGSystem object but got something else")
        return
    
    # Initialize session state for chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            
            # Show additional info for assistant messages
            if message["role"] == "assistant":
                # Show sources for responses
                if "sources" in message:
                    display_sources(message["sources"])
    
    # Handle sample question selection
    selected_question = None
    if len(st.session_state.messages) == 0:
        selected_question = display_sample_questions()
    
    # Chat input
    prompt = st.chat_input("Ask a question about physiology...")
    
    # Use selected question if available
    if selected_question:
        prompt = selected_question
    
    if prompt:
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Generate response
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            status_placeholder = st.empty()
            
            try:
                status_placeholder.info("🤖 Processing with Coordinator Agent...")
                
                # Verify RAG system is properly initialized
                if not rag_system or not hasattr(rag_system, 'answer_question'):
                    status_placeholder.error("RAG system not properly initialized")
                    st.error("System error: RAG system not available")
                    return
                
                # For now, use direct RAG system (agent integration coming soon)
                status_placeholder.info(f"🔍 Searching documents with RAG system ({num_sources} sources)...")
                logger.info(f"Using {num_sources} sources for query: {prompt[:50]}...")
                result = rag_system.answer_question(prompt, num_sources)
                
                # TODO: Re-enable agent system once Streamlit async issues are resolved
                # try:
                #     # Get agent and context for this session
                #     coordinator, context = init_agent_for_session(rag_system)
                #     result = await coordinator.handle_conversation(prompt, context)
                # except Exception as agent_error:
                #     logger.error(f"Agent system failed, using direct RAG: {agent_error}")
                #     result = rag_system.answer_question(prompt, num_sources)
                
                status_placeholder.info("✅ Response generated!")
                
                # Handle RAG response (agent integration disabled for now)
                if result.get('error') or "Error" in result.get("answer", ""):
                    message_placeholder.error(result["answer"])
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": result["answer"]
                    })
                else:
                    # Display answer
                    message_placeholder.markdown(result["answer"])
                    
                    # Display sources
                    if result.get("sources"):
                        display_sources(result["sources"])
                    
                    # Add assistant message to chat history
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": result["answer"],
                        "sources": result.get("sources", []),
                        "agent_response": False
                    })
                    
                    # Show agent system note
                    st.info("🤖 Agent system integration temporarily disabled for Streamlit compatibility. Using direct RAG system.")
                
                # Clear status
                status_placeholder.empty()
                
            except Exception as e:
                error_msg = f"Streamlit error: {str(e)}"
                logger.error(error_msg)
                message_placeholder.error(error_msg)
                status_placeholder.empty()
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": error_msg
                })
    
    # Footer
    st.markdown("---")
    st.markdown(
        "Built with ❤️ for medical education | "
        "**MedMind** Multi-Agent AI Platform | "
        "[Documentation](docs/) | "
        "[GitHub](https://github.com/keentechcodes/MedMind)"
    )


if __name__ == "__main__":
    main()