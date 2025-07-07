"""
CLI interface for testing the Coordinator Agent.
Provides a simple command-line interface to interact with MedMind agents.
"""

import asyncio
import os
import re
from pathlib import Path

from physiology_rag.agents.coordinator import create_coordinator_agent
from physiology_rag.core.rag_system import RAGSystem
from physiology_rag.core.paragraph_extractor import ParagraphExtractor
from physiology_rag.config.settings import get_settings
from physiology_rag.utils.logging import get_logger

logger = get_logger("agent_cli")


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


def display_sources_cli(sources):
    """Display source information in CLI format like Streamlit."""
    if not sources:
        print("No sources found.")
        return
        
    print("\n📚 Sources:")
    print("=" * 60)
    
    for i, source in enumerate(sources):
        score = source.get('similarity_score', 0.0)
        doc_name = source.get('metadata', {}).get('document_name', 'Unknown Document')
        metadata = source.get('metadata', {})
        
        # Extract meaningful section title
        section_title = metadata.get('title', 'Content')
        if section_title == 'Content' or not section_title:
            chunk_text = source.get('document', '')
            section_title = extract_section_title_from_text(chunk_text)
        
        print(f"\nSource {i+1}: {doc_name} (Score: {score:.3f})")
        print(f"Section: {section_title}")
        print(f"Chunk: {metadata.get('chunk_index', '?')}/{metadata.get('total_chunks', '?')}")
        print(f"Chunk Type: {metadata.get('chunk_type', 'content')}")
        print(f"\nFull Content:")
        print("=" * 40)
        print(source.get('document', 'No content available'))
        
        # Show images for this source like Streamlit does
        print(f"\nImages from {doc_name}:")
        print("=" * 30)
        try:
            # Try to get images (simplified version for CLI)
            from pathlib import Path
            import json
            
            # Load processed documents to get image info
            processed_file = Path("data/processed/processed_documents.json")
            if processed_file.exists():
                with open(processed_file, "r") as f:
                    docs = json.load(f)
                
                # Find images for this document
                doc_images = []
                for doc in docs:
                    if doc.get('document_name') == doc_name:
                        doc_images = doc.get('images', [])[:3]  # First 3 like Streamlit
                        break
                
                if doc_images:
                    for img in doc_images:
                        print(f"  - {img.get('type', 'Unknown')} {img.get('number', '?')}: {img.get('filename', 'No filename')}")
                        print(f"    Path: {img.get('path', 'No path')}")
                else:
                    print("  No images found for this document")
            else:
                print("  Cannot load image information")
                
        except Exception as e:
            print(f"  Error loading images: {e}")
        
        print("-" * 60)


async def test_rag_with_sources():
    """Test RAG system directly to see source attribution like Streamlit."""
    print("🧪 Testing RAG System with Enhanced Source Display")
    print("=" * 55)
    
    try:
        # Initialize system
        settings = get_settings()
        
        if not settings.gemini_api_key:
            print("❌ Error: GEMINI_API_KEY not found.")
            return
        
        rag_system = RAGSystem(settings.gemini_api_key)
        print("✅ RAG system initialized")
        
        # Test with blood-brain barrier question
        test_question = "How does the blood-brain barrier protect neurons while allowing glucose transport?"
        print(f"\n🧪 Testing question: {test_question}")
        
        # Get RAG response like Streamlit does
        result = rag_system.answer_question(test_question, 3)
        
        # Display answer
        print("\n🧠 Answer:")
        print("=" * 40)
        print(result.get('answer', 'No answer generated'))
        
        # Display sources with enhanced titles
        sources = result.get('sources', [])
        display_sources_cli(sources)
        
        print("\n🎉 Testing completed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        logger.error(f"Testing error: {e}")


async def test_paragraph_extraction():
    """Test paragraph extraction on RAG sources."""
    print("🧪 Testing Paragraph Extraction")
    print("=" * 40)
    
    try:
        # Initialize system
        settings = get_settings()
        
        if not settings.gemini_api_key:
            print("❌ Error: GEMINI_API_KEY not found.")
            return
        
        rag_system = RAGSystem(settings.gemini_api_key)
        paragraph_extractor = ParagraphExtractor()
        print("✅ Systems initialized")
        
        # Test with blood-brain barrier question
        test_question = "How does the blood-brain barrier protect neurons while allowing glucose transport?"
        print(f"\n🧪 Testing question: {test_question}")
        
        # Get RAG sources only (no answer generation)
        sources = rag_system.retrieve_relevant_chunks(test_question, 3)
        source_list = sources.get('results', [])
        
        if not source_list:
            print("❌ No sources found!")
            return
            
        print(f"\n📚 Found {len(source_list)} sources")
        
        # Extract paragraphs from sources
        paragraphs = paragraph_extractor.extract_paragraphs_from_sources(source_list)
        
        print(f"\n📄 Extracted {len(paragraphs)} paragraphs")
        print("=" * 50)
        
        # Display paragraphs
        for i, paragraph in enumerate(paragraphs):
            print(f"\n📄 Paragraph {i+1}: {paragraph.document_name}")
            print(f"Section: {paragraph.title}")
            print(f"Source Chunk: {paragraph.source_chunk_index}")
            print(f"Paragraph Index: {paragraph.paragraph_index}")
            print(f"Content Length: {len(paragraph.content)} chars")
            print(f"\nContent Preview:")
            print("-" * 30)
            # Show first 200 chars
            preview = paragraph.content[:200] + "..." if len(paragraph.content) > 200 else paragraph.content
            print(preview)
            print("-" * 50)
        
        print("\n🎉 Paragraph extraction testing completed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        logger.error(f"Paragraph extraction error: {e}")


async def interactive_session():
    """Run an interactive session with the Coordinator Agent."""
    print("🧠 MedMind Coordinator Agent - Interactive Mode")
    print("=" * 50)
    
    try:
        # Initialize system
        print("Initializing MedMind system...")
        settings = get_settings()
        
        if not settings.gemini_api_key:
            print("❌ Error: GEMINI_API_KEY not found in environment variables.")
            print("Please set your Gemini API key in .env file or environment.")
            return
        
        # Create RAG system
        rag_system = RAGSystem(settings.gemini_api_key)
        
        # Create coordinator agent
        coordinator, context = create_coordinator_agent(
            rag_system=rag_system,
            user_id="cli_user"
        )
        
        print("✅ MedMind system initialized successfully!")
        print("\nYou can now ask questions about physiology.")
        print("Try questions like:")
        print("  - 'Explain how synaptic transmission works'")
        print("  - 'Quiz me on neurophysiology'")
        print("  - 'How am I doing with my learning progress?'")
        print("\nType 'exit' to quit.\n")
        
        # Interactive loop
        while True:
            try:
                user_input = input("🎓 You: ").strip()
                
                if user_input.lower() in ['exit', 'quit', 'bye']:
                    print("👋 Goodbye! Happy learning!")
                    break
                
                if not user_input:
                    continue
                
                print("🤖 MedMind is thinking...")
                
                # Process user input
                response = await coordinator.handle_conversation(user_input, context)
                
                print(f"🧠 MedMind: {response}\n")
                
            except KeyboardInterrupt:
                print("\n👋 Goodbye! Happy learning!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                logger.error(f"Error in interactive session: {e}")
    
    except Exception as e:
        print(f"❌ Failed to initialize MedMind: {e}")
        logger.error(f"Initialization error: {e}")


async def test_coordinator():
    """Run basic tests of the coordinator agent."""
    print("🧪 Testing MedMind Coordinator Agent")
    print("=" * 40)
    
    try:
        # Initialize system
        settings = get_settings()
        
        if not settings.gemini_api_key:
            print("❌ Error: GEMINI_API_KEY not found.")
            return
        
        rag_system = RAGSystem(settings.gemini_api_key)
        coordinator, context = create_coordinator_agent(rag_system, "test_user")
        
        print("✅ Coordinator agent initialized")
        
        # Test cases
        test_cases = [
            "Explain neurophysiology basics",
            "Can you quiz me on synaptic transmission?",
            "How am I doing with my progress?",
            "What is the action potential?"
        ]
        
        for i, test_input in enumerate(test_cases, 1):
            print(f"\n🧪 Test {i}: {test_input}")
            try:
                response = await coordinator.handle_conversation(test_input, context)
                print(f"✅ Response: {response[:100]}...")
            except Exception as e:
                print(f"❌ Error: {e}")
        
        print("\n🎉 Testing completed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        logger.error(f"Testing error: {e}")


def show_system_info():
    """Show system information and status."""
    print("🔍 MedMind System Information")
    print("=" * 35)
    
    try:
        settings = get_settings()
        
        print(f"📁 Working directory: {Path.cwd()}")
        print(f"🔑 API key configured: {'Yes' if settings.gemini_api_key else 'No'}")
        print(f"🤖 Model: {settings.gemini_model_name}")
        print(f"📊 Max context length: {settings.max_context_length}")
        print(f"🔍 Max retrieval results: {settings.max_retrieval_results}")
        
        # Check for vector database
        chroma_path = Path("./chroma_db")
        print(f"📚 Vector database: {'Found' if chroma_path.exists() else 'Not found'}")
        
        # Check for processed documents
        output_path = Path("./output")
        if output_path.exists():
            doc_count = len([d for d in output_path.iterdir() if d.is_dir()])
            print(f"📄 Processed documents: {doc_count}")
        else:
            print("📄 Processed documents: 0")
        
    except Exception as e:
        print(f"❌ Error getting system info: {e}")


async def main_async():
    """Async main CLI entry point."""
    import sys
    
    if len(sys.argv) < 2:
        await interactive_session()
        return
    
    command = sys.argv[1].lower()
    
    if command == "test":
        await test_coordinator()
    elif command == "test-sources":
        await test_rag_with_sources()
    elif command == "test-paragraphs":
        await test_paragraph_extraction()
    elif command == "info":
        show_system_info()
    elif command == "interactive":
        await interactive_session()
    else:
        print("🔧 MedMind Coordinator Agent CLI")
        print("\nAvailable commands:")
        print("  medmind-cli                      # Interactive mode")
        print("  medmind-cli test                # Run tests")
        print("  medmind-cli test-sources        # Test RAG with enhanced sources")
        print("  medmind-cli test-paragraphs     # Test paragraph extraction")
        print("  medmind-cli info                # System info")
        print("  medmind-cli interactive         # Interactive mode")


def main():
    """Sync main entry point for package scripts."""
    asyncio.run(main_async())


if __name__ == "__main__":
    main()