"""
CLI interface for testing the Coordinator Agent.
Provides a simple command-line interface to interact with MedMind agents.
"""

import asyncio
import os
from pathlib import Path

from physiology_rag.agents.coordinator import create_coordinator_agent
from physiology_rag.core.rag_system import RAGSystem
from physiology_rag.config.settings import get_settings
from physiology_rag.utils.logging import get_logger

logger = get_logger("agent_cli")


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


async def main():
    """Main CLI entry point."""
    import sys
    
    if len(sys.argv) < 2:
        await interactive_session()
        return
    
    command = sys.argv[1].lower()
    
    if command == "test":
        await test_coordinator()
    elif command == "info":
        show_system_info()
    elif command == "interactive":
        await interactive_session()
    else:
        print("🔧 MedMind Coordinator Agent CLI")
        print("\nAvailable commands:")
        print("  python -m physiology_rag.agents.cli           # Interactive mode")
        print("  python -m physiology_rag.agents.cli test      # Run tests")
        print("  python -m physiology_rag.agents.cli info      # System info")
        print("  python -m physiology_rag.agents.cli interactive  # Interactive mode")


if __name__ == "__main__":
    asyncio.run(main())