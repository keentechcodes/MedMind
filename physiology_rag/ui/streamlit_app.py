#!/usr/bin/env python3
"""
Streamlit Chat Interface for Physiology RAG System
"""

import json
import streamlit as st
from pathlib import Path

from physiology_rag.core.rag_system import RAGSystem
from physiology_rag.config.settings import get_settings
from physiology_rag.utils.logging import get_logger

# Setup logging
logger = get_logger("streamlit_app")

# Get settings
settings = get_settings()

# Page config
st.set_page_config(
    page_title=settings.streamlit_title,
    page_icon=settings.streamlit_icon,
    layout="wide",
    initial_sidebar_state="expanded"
)


@st.cache_resource
def init_rag_system():
    """Initialize RAG system with caching."""
    try:
        logger.info("Initializing RAG system for Streamlit")
        return RAGSystem()
    except Exception as e:
        logger.error(f"Failed to initialize RAG system: {e}")
        st.error(f"Failed to initialize RAG system: {e}")
        return None


def display_sources(sources):
    """Display source information in a nice format."""
    st.subheader("📚 Sources")
    
    for i, source in enumerate(sources):
        score = source['similarity_score']
        doc_name = source['metadata']['document_name']
        
        with st.expander(f"Source {i+1}: {doc_name} (Score: {score:.3f})"):
            st.write("**Section:**", source['metadata'].get('title', 'Content'))
            st.write("**Page:**", source['metadata'].get('page_id', 'Unknown'))
            st.write("**Chunk Type:**", source['metadata'].get('chunk_type', 'content'))
            st.write("**Content:**")
            st.write(source['document'])


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
            
            # Show first few documents
            st.write("**Documents:**")
            for doc in docs[:5]:
                doc_name = doc.get('document_name', 'Unknown')
                chunks = doc.get('total_chunks', 0)
                images = doc.get('total_images', 0)
                st.write(f"• {doc_name}")
                st.write(f"  └ {chunks} sections, {images} images")
            
            if len(docs) > 5:
                st.write(f"... and {len(docs) - 5} more documents")
        
        st.markdown("---")
        st.header("⚙️ Settings")
        
        # Settings controls
        num_sources = st.slider(
            "Number of sources to retrieve", 
            1, 10, 
            min(settings.max_retrieval_results, 5)
        )
        
        # Show system info
        st.markdown("---")
        st.header("ℹ️ System Info")
        st.write(f"**Model:** {settings.gemini_model_name}")
        st.write(f"**Embedding Model:** {settings.gemini_embedding_model}")
        st.write(f"**Max Context:** {settings.max_context_length} chars")
        
        return num_sources


def display_sample_questions():
    """Display sample questions when chat is empty."""
    st.markdown("### 💡 Try asking about:")
    
    sample_questions = [
        "What is the cerebral cortex and what are its main functions?",
        "How does the blood-brain barrier work?",
        "Explain the role of the hypothalamus in thermoregulation",
        "What are the different types of memory and where are they stored?",
        "How does vision processing work in the brain?",
        "Describe the structure and function of neurons",
        "What is the autonomic nervous system?",
        "How does synaptic transmission occur?"
    ]
    
    cols = st.columns(2)
    for i, question in enumerate(sample_questions):
        col = cols[i % 2]
        if col.button(question, key=f"sample_{i}", use_container_width=True):
            return question
    
    return None


def main():
    """Main Streamlit application."""
    # Title and description
    st.title(settings.streamlit_title)
    st.markdown("Ask questions about physiology concepts and get answers based on lecture documents.")
    
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
    
    # Display sidebar and get settings
    num_sources = display_sidebar()
    if num_sources is None:
        return
    
    # Initialize RAG system
    rag_system = init_rag_system()
    if rag_system is None:
        st.error("Cannot proceed without RAG system initialization")
        return
    
    # Initialize session state for chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            
            # Show sources for assistant messages
            if message["role"] == "assistant" and "sources" in message:
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
                status_placeholder.info("🔍 Searching documents...")
                
                # Get answer from RAG system
                result = rag_system.answer_question(prompt, num_sources)
                
                status_placeholder.info("✅ Response generated!")
                
                # Check for errors
                if result.get('error') or "Error" in result.get("answer", ""):
                    message_placeholder.error(result["answer"])
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": result["answer"]
                    })
                else:
                    # Display answer
                    message_placeholder.markdown(result["answer"])
                    
                    # Clear status
                    status_placeholder.empty()
                    
                    # Display sources
                    if result.get("sources"):
                        display_sources(result["sources"])
                    
                    # Add assistant message to chat history
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": result["answer"],
                        "sources": result.get("sources", [])
                    })
                
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
        "[Documentation](docs/) | "
        "[Report Issues](https://github.com/yourusername/physiology-rag/issues)"
    )


if __name__ == "__main__":
    main()