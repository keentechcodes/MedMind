#!/usr/bin/env python3
"""
MedMind - AI-Powered Medical Education Assistant
Multi-Agent Streamlit Interface with PydanticAI Integration
"""

import json
import re
import asyncio
import streamlit as st
from pathlib import Path
from typing import Dict, Any, Optional

from physiology_rag.core.rag_system import RAGSystem
from physiology_rag.core.paragraph_extractor import ParagraphExtractor
from physiology_rag.core.answer_attribution import AnswerAttributionMapper
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
def init_enhanced_citation_system():
    """Initialize Enhanced Citation System with paragraph extraction and attribution."""
    try:
        logger.info("Initializing Enhanced Citation System for Streamlit")
        
        # Check settings first
        settings = get_settings()
        logger.info(f"API key available: {bool(settings.gemini_api_key and settings.gemini_api_key != 'your-gemini-api-key-here')}")
        
        # Initialize RAG system
        rag_system = RAGSystem()
        logger.info(f"RAG system type: {type(rag_system)}")
        
        # Initialize paragraph extractor
        paragraph_extractor = ParagraphExtractor()
        logger.info("Paragraph extractor initialized")
        
        # Initialize answer attribution mapper
        attribution_mapper = AnswerAttributionMapper(settings.gemini_api_key)
        logger.info("Answer attribution mapper initialized")
        
        # Verify the RAG system has the required methods
        if not hasattr(rag_system, 'answer_question'):
            raise AttributeError("RAGSystem does not have answer_question method")
        
        logger.info("Enhanced citation system initialized successfully")
        return {
            'rag_system': rag_system,
            'paragraph_extractor': paragraph_extractor,
            'attribution_mapper': attribution_mapper
        }
        
    except Exception as e:
        logger.error(f"Failed to initialize enhanced citation system: {e}")
        logger.error(f"Exception type: {type(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        st.error(f"Failed to initialize enhanced citation system: {e}")
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

def extract_section_title_from_text(text: str) -> str:
    """Extract a meaningful section title from chunk text."""
    if not text:
        return "Content"
    
    lines = text.strip().split('\n')
    
    # Try different patterns in order of preference
    for line in lines[:10]:  # Check first 10 lines
        line = line.strip()
        if not line:
            continue
            
        # Pattern 1: Markdown headers (##, ###, ####)
        if re.match(r'^#{2,4}\s+(.+)', line):
            title = re.sub(r'^#{2,4}\s+', '', line).strip()
            if len(title) > 3:
                return title
        
        # Pattern 2: Bold headers (**text**)
        bold_match = re.match(r'^\*\*(.+?)\*\*', line)
        if bold_match:
            title = bold_match.group(1).strip()
            if len(title) > 3 and not title.isdigit():
                return title
        
        # Pattern 3: Numbered sections (1., 2., etc.)
        numbered_match = re.match(r'^\d+\.\s+(.+)', line)
        if numbered_match:
            title = numbered_match.group(1).strip()
            if len(title) > 3:
                return title
        
        # Pattern 4: Bullet points with caps (● Text, - Text)
        bullet_match = re.match(r'^[●•-]\s*(.+)', line)
        if bullet_match:
            title = bullet_match.group(1).strip()
            if len(title) > 3 and title[0].isupper():
                return title
        
        # Pattern 5: All caps headers
        if line.isupper() and len(line) > 3 and len(line) < 80:
            return line
        
        # Pattern 6: Title case headers (first significant line)
        if (len(line) > 5 and len(line) < 100 and 
            line[0].isupper() and 
            not line.endswith('.') and 
            not line.startswith('Source') and
            not line.startswith('Figure')):
            return line
    
    # Fallback: use first meaningful line
    for line in lines[:5]:
        line = line.strip()
        if len(line) > 10 and not line.startswith('|') and not line.startswith('![]'):
            return line[:50] + "..." if len(line) > 50 else line
    
    return "Content"


def display_attributed_answer(attributed_answer_data):
    """Display answer with enhanced paragraph-level citations."""
    if not attributed_answer_data:
        st.error("No attributed answer data available")
        return
    
    answer = attributed_answer_data.get('answer', '')
    attributions = attributed_answer_data.get('attributions', [])
    overall_confidence = attributed_answer_data.get('overall_confidence', 0.0)
    
    # Display the answer with inline citations
    st.subheader("🧠 Enhanced Answer with Precise Citations")
    
    # Show overall confidence
    confidence_color = "green" if overall_confidence > 0.8 else "orange" if overall_confidence > 0.6 else "red"
    st.markdown(f"**Overall Citation Confidence:** :{confidence_color}[{overall_confidence:.2f}]")
    
    # Display answer segments with their citations
    for i, attribution in enumerate(attributions):
        segment = attribution.get('segment', '')
        supporting_paragraphs = attribution.get('supporting_paragraphs', [])
        confidence = attribution.get('confidence', 0.0)
        attr_type = attribution.get('type', 'unknown')
        
        # Create expandable section for each segment
        with st.expander(f"📄 Answer Segment {i+1} - {attr_type.title()} (Confidence: {confidence:.2f})", expanded=True):
            # Display the segment text
            st.markdown(segment)
            
            # Display supporting paragraphs
            if supporting_paragraphs:
                st.markdown("**🎯 Supported by:**")
                
                for j, para_info in enumerate(supporting_paragraphs):
                    para_title = para_info.get('title', 'Unknown Section')
                    para_doc = para_info.get('document', 'Unknown Document')
                    para_preview = para_info.get('content_preview', '')
                    
                    # Color-code by confidence
                    conf_color = "green" if confidence > 0.8 else "orange" if confidence > 0.6 else "red"
                    
                    st.markdown(f"**{j+1}.** :{conf_color}[{para_title}] from *{para_doc}*")
                    
                    with st.expander(f"Preview: {para_title}", expanded=False):
                        st.write(para_preview)
            else:
                st.warning("No supporting paragraphs identified for this segment")


def display_enhanced_sources(attributed_answer):
    """Display paragraph-level sources with enhanced organization."""
    if not attributed_answer or not hasattr(attributed_answer, 'paragraphs'):
        return
    
    st.subheader("📚 Paragraph-Level Sources")
    
    paragraphs = attributed_answer.paragraphs
    
    # Group paragraphs by document
    doc_paragraphs = {}
    for paragraph in paragraphs:
        doc_name = paragraph.document_name
        if doc_name not in doc_paragraphs:
            doc_paragraphs[doc_name] = []
        doc_paragraphs[doc_name].append(paragraph)
    
    # Display by document
    for doc_name, paras in doc_paragraphs.items():
        with st.expander(f"📄 {doc_name} ({len(paras)} paragraphs)", expanded=False):
            
            # Show document images
            doc_images = get_images_for_document(doc_name, max_images=3)
            if doc_images:
                found_images = [img for img in doc_images if 'working_path' in img]
                if found_images:
                    st.write(f"**Document Images:** ({len(found_images)} available)")
                    cols = st.columns(min(len(found_images), 3))
                    for j, img in enumerate(found_images[:3]):
                        try:
                            cols[j].image(
                                img['working_path'], 
                                caption=f"{img['type']} {img['number']}",
                                width=150
                            )
                        except Exception as e:
                            cols[j].write(f"Image error: {e}")
            
            # Display paragraphs
            for i, para in enumerate(paras):
                st.markdown(f"**Paragraph {i+1}: {para.title}**")
                st.markdown(f"*Source chunk: {para.source_chunk_index}, Paragraph: {para.paragraph_index}*")
                
                with st.expander(f"Content: {para.title}", expanded=False):
                    st.write(para.content)
                
                st.markdown("---")


def display_sources(sources):
    """Display source information in a nice format with associated images (legacy function)."""
    if not sources:
        return
        
    st.subheader("📚 Legacy Sources Display")
    st.info("This is the old source display. Enhanced paragraph-level citations are shown above.")
    
    for i, source in enumerate(sources):
        score = source.get('similarity_score', 0.0)
        doc_name = source.get('metadata', {}).get('document_name', 'Unknown Document')
        
        with st.expander(f"Source {i+1}: {doc_name} (Score: {score:.3f})"):
            metadata = source.get('metadata', {})
            chunk_info = f"{metadata.get('chunk_index', '?')}/{metadata.get('total_chunks', '?')}"
            
            # Extract meaningful section title
            section_title = metadata.get('title', 'Content')
            if section_title == 'Content' or not section_title:
                chunk_text = source.get('document', '')
                section_title = extract_section_title_from_text(chunk_text)
            
            st.write("**Section:**", section_title)
            st.write("**Chunk:**", f"{metadata.get('chunk_index', '?')}/{metadata.get('total_chunks', '?')}")
            st.write("**Chunk Type:**", metadata.get('chunk_type', 'content'))
            
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
        st.header("🎯 Enhanced Citation System")
        st.write("**🆕 NEW:** Paragraph-level citations")
        st.write("**🔍 Features:** Answer attribution mapping")
        st.write("**🎯 Precision:** Segment-to-paragraph matching")
        st.write("**📊 Confidence:** Attribution scoring")
        
        st.markdown("---")
        st.header("🤖 Agent System")
        st.write("**Architecture:** Multi-Agent PydanticAI")
        st.write("**🔄 Status:** Temporary RAG-only mode")
        st.write("**🔍 Available:** Document Q&A with Enhanced Citations")
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
    
    # Initialize Enhanced Citation System
    citation_systems = init_enhanced_citation_system()
    if citation_systems is None:
        st.error("Cannot proceed without enhanced citation system initialization")
        st.info("Please check your .env file and ensure GEMINI_API_KEY is set correctly")
        return
    
    rag_system = citation_systems['rag_system']
    paragraph_extractor = citation_systems['paragraph_extractor']
    attribution_mapper = citation_systems['attribution_mapper']
    
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
            # Show additional info for assistant messages
            if message["role"] == "assistant":
                # Check if this message has enhanced citations
                if message.get("enhanced_citations") and "attributed_answer" in message:
                    # Display enhanced answer with attributions
                    display_attributed_answer(message["attributed_answer"])
                    
                    # Note: enhanced sources would need the attributed_answer object
                    # For now, show legacy sources for chat history
                    if "sources" in message:
                        display_sources(message["sources"])
                else:
                    # Regular display for non-enhanced messages
                    st.markdown(message["content"])
                    
                    # Show sources for responses
                    if "sources" in message:
                        display_sources(message["sources"])
            else:
                # User messages
                st.markdown(message["content"])
    
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
        
        # Generate response with enhanced citations
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            status_placeholder = st.empty()
            
            try:
                status_placeholder.info("🤖 Processing with Enhanced Citation System...")
                
                # Verify systems are properly initialized
                if not rag_system or not hasattr(rag_system, 'answer_question'):
                    status_placeholder.error("RAG system not properly initialized")
                    st.error("System error: RAG system not available")
                    return
                
                # Step 1: Get RAG answer and sources
                status_placeholder.info(f"🔍 Step 1: Searching documents ({num_sources} sources)...")
                logger.info(f"Using {num_sources} sources for query: {prompt[:50]}...")
                result = rag_system.answer_question(prompt, num_sources)
                
                if result.get('error') or "Error" in result.get("answer", ""):
                    message_placeholder.error(result["answer"])
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": result["answer"]
                    })
                    status_placeholder.empty()
                    return
                
                answer = result.get('answer', '')
                sources = result.get('sources', [])
                
                # Step 2: Extract paragraphs
                status_placeholder.info("📄 Step 2: Extracting paragraphs...")
                paragraphs = paragraph_extractor.extract_paragraphs_from_sources(sources)
                logger.info(f"Extracted {len(paragraphs)} paragraphs from {len(sources)} sources")
                
                # Step 3: Create attributed answer
                status_placeholder.info("🎯 Step 3: Creating answer attribution...")
                
                # Use asyncio to handle the async function
                import asyncio
                try:
                    # Try to get the current event loop, create one if it doesn't exist
                    try:
                        loop = asyncio.get_event_loop()
                    except RuntimeError:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                    
                    attributed_answer = loop.run_until_complete(
                        attribution_mapper.create_attributed_answer(prompt, answer, paragraphs)
                    )
                except Exception as async_error:
                    logger.error(f"Attribution async error: {async_error}")
                    # Fallback to basic display
                    attributed_answer = None
                
                status_placeholder.info("✅ Enhanced response generated!")
                
                # Step 4: Display enhanced results
                if attributed_answer:
                    # Format for display
                    attributed_answer_data = attribution_mapper.format_attributed_answer_for_display(attributed_answer)
                    
                    # Display enhanced answer with attributions
                    display_attributed_answer(attributed_answer_data)
                    
                    # Display enhanced paragraph-level sources
                    display_enhanced_sources(attributed_answer)
                    
                    # Add to chat history with enhanced data
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": answer,
                        "sources": sources,
                        "attributed_answer": attributed_answer_data,
                        "enhanced_citations": True
                    })
                else:
                    # Fallback to basic display
                    st.warning("Attribution mapping failed, showing basic citations")
                    message_placeholder.markdown(answer)
                    display_sources(sources)
                    
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": answer,
                        "sources": sources,
                        "enhanced_citations": False
                    })
                
                # Clear status
                status_placeholder.empty()
                
            except Exception as e:
                error_msg = f"Enhanced citation error: {str(e)}"
                logger.error(error_msg)
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
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