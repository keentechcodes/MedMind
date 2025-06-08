# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a professionally structured AI-powered medical education platform designed specifically for physiology learning. The system uses a **multi-agent architecture with PydanticAI** to provide personalized, adaptive learning experiences including quiz generation, progress tracking, and intelligent tutoring for medical students.

**🤖 AGENTIC ARCHITECTURE**: Now implements specialized AI agents using PydanticAI framework for coordinated, intelligent learning assistance with type-safe operations and natural conversation flows.

## Architecture

The system implements a **multi-agent architecture** with specialized AI agents coordinating to provide comprehensive learning experiences:

1. **Coordinator Agent**: Main orchestrator that routes requests to specialized agents based on learning intent
2. **Quiz Agent**: Generates adaptive quizzes with difficulty progression and detailed explanations
3. **Progress Agent**: Tracks learning analytics, mastery scores, and spaced repetition scheduling
4. **Tutor Agent**: Provides personalized explanations and contextual question answering
5. **Validation Agent**: Ensures medical accuracy and fact-checking against authoritative sources

**Foundation Components**:
- **RAG System**: PDF processing, document chunking, and vector database (ChromaDB + Gemini embeddings)
- **PydanticAI Framework**: Type-safe agent coordination with dependency injection and tool integration
- **Learning Analytics**: SQLite-based progress tracking and adaptive algorithms

### Core Components

**Agentic Package Layout:**
- `physiology_rag/agents/`: **PydanticAI agent implementations** (coordinator, quiz, progress, tutor, validation)
- `physiology_rag/dependencies/`: **Shared context and data** (medical context, user profiles, RAG integration)
- `physiology_rag/config/`: Configuration management with environment variables
- `physiology_rag/core/`: Foundation RAG system (document processing, embeddings, vector database)
- `physiology_rag/learning/`: **Learning analytics** (progress tracking, spaced repetition, mastery scoring)
- `physiology_rag/ui/`: Enhanced interface with agent integration
- `physiology_rag/utils/`: Logging and utility functions

**Key Features:**
- ✅ **Multi-Agent Architecture**: Specialized PydanticAI agents for different learning tasks
- ✅ **Adaptive Learning**: Quiz generation, progress tracking, spaced repetition
- ✅ **Type-Safe Operations**: Pydantic models for validated inputs/outputs
- ✅ **Conversational Memory**: Multi-turn interactions with context preservation
- ✅ **Medical Validation**: Fact-checking and expert review workflows
- ✅ **Environment-based Configuration**: No hardcoded API keys
- ✅ **Comprehensive Testing**: pytest with agent mocking and integration tests

### Agentic Data Flow

**Foundation Layer:**
1. PDFs (`data/raw/`) → marker-pdf converter → Markdown + Images + Metadata (`data/processed/`)
2. Markdown → DocumentProcessor → Section-based chunks → ChromaDB (`data/vector_db/`)

**Agent Interaction Layer:**
3. User Input → **Coordinator Agent** → Routes to appropriate specialist agent
4. **Quiz Agent** → RAG retrieval + question generation → Structured quiz output
5. **Progress Agent** → Learning analytics + mastery tracking → Progress updates
6. **Tutor Agent** → Contextual explanation + source attribution → Educational response
7. All interactions → **Learning Database** (`data/user_data/`) → Personalization data

## Key Commands

### Environment Setup
```bash
# Install the package and dependencies (includes PydanticAI)
pip install -e .

# Copy environment template and configure
cp .env.example .env
# Edit .env with your GEMINI_API_KEY

# Development setup with PydanticAI testing tools
pip install -e .[dev]
```

### Quick Start
```bash
# Complete system setup (one command!)
python scripts/setup.py

# Launch MedMind with agent coordination
streamlit run physiology_rag/ui/streamlit_app.py

# Or use the coordinator agent directly
python -m physiology_rag.agents.coordinator
```

### Agent Commands
```bash
# Test individual agents
medmind-quiz --topic "neurophysiology" --count 5
medmind-progress --user-id "student123"
medmind-tutor --question "How does synaptic transmission work?"

# Run agent integration tests
pytest tests/test_agents/

# Test agent coordination
pytest tests/test_agent_coordination.py
```

### Development Commands
```bash
# Code formatting
black physiology_rag/
isort physiology_rag/

# Type checking
mypy physiology_rag/

# Run all quality checks
pre-commit run --all-files
```

## Configuration Details

### Google AI Services
- Uses `text-embedding-004` for embeddings via Gemini API
- PDF conversion enhanced with `gemini-2.5-flash-preview-04-17`
- Simple API key authentication (no Google Cloud setup required)

### Document Processing
- **Enhanced Metadata-Based Chunking**: Uses table_of_contents from marker-pdf metadata
- **Section-Aware Chunks**: Splits content by actual document sections and page boundaries
- **Fallback Chunking**: Simple sentence-based chunking when metadata unavailable
- **Image Metadata**: Extracted with page/figure numbering and contextual linking
- Chunk size: 1000 characters maximum per section

### Vector Database
- ChromaDB with cosine similarity
- Collection name: `physiology_documents`
- Persistent storage in `./chroma_db/`

### RAG System
- **Response Generation**: Gemini 2.0 Flash for natural language answers
- **Context Integration**: Combines multiple relevant sources with citations (max 3 sources, 3000 char limit)
- **Source Attribution**: Shows document names, sections, and relevance scores
- **Interactive Interface**: Streamlit chat UI with conversation history and working sample questions
- **Performance**: Optimized prompts and error handling for reliable operation

## Data Structure

The `output/` directory contains subdirectories for each processed PDF:
```
output/
├── PHY 6.01 Overview of Neurophysiology/
│   ├── PHY 6.01 Overview of Neurophysiology.md
│   ├── _page_X_Figure_Y.jpeg
│   └── metadata.txt
```

The system expects this specific structure for proper document processing and image linking.

## Usage

### Quick Start
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Test the complete system
streamlit run physiology_rag/ui/streamlit_app.py
```

### System Status
✅ **PDF Processing**: 13 physiology documents converted with metadata  
✅ **Document Processing**: 643 section-based chunks created  
✅ **Vector Database**: ChromaDB with 643 embeddings ready  
✅ **RAG System**: Working question-answering with source citations  
✅ **Streamlit Interface**: Functional chat UI with sample questions  

The system is fully operational and ready for physiology Q&A!

### Examples and Testing
✅ **Example Scripts**: Debugging and demo scripts in `examples/` directory  
✅ **Test Suite**: Unit tests and integration tests in `tests/` directory  
✅ **Clean Root Directory**: No cluttered script files in project root

## Recent Updates

### Enhanced Document Processing (Latest)
- **Metadata Integration**: Now uses rich metadata from marker-pdf (table_of_contents, page_stats)
- **Structured Chunking**: Creates chunks based on actual document sections instead of arbitrary splits
- **Better Context**: Each chunk includes section title, page_id, and content type
- **Improved Retrieval**: Section-based chunks provide better semantic context for RAG

### Gemini API Integration
- **Simplified Authentication**: Switched from Vertex AI to Gemini API for easier setup
- **No Google Cloud Required**: Uses direct API key authentication
- **Better Embeddings**: Uses latest `text-embedding-004` model with task-specific optimization

### Complete RAG System (Latest)
- **Full Pipeline**: Added `physiology_rag/core/rag_system.py` for end-to-end question answering
- **Streamlit Interface**: Professional chat UI with source citations and conversation history
- **Context-Aware Responses**: Gemini 2.0 Flash generates answers using retrieved document sections
- **Source Attribution**: Shows exactly which documents and sections were used for each answer
- **Interactive Experience**: Real-time chat with expandable source details and working sample questions
- **Performance Optimized**: Simplified prompts and context limits for reliable operation

## Future Feature Concept

- Designed for medical students to upload additional documents
- Will function as a multi-modal learning assistant with features including:
  - Contextual chatbot for document-based Q&A
  - Quiz generation from uploaded materials
  - Flashcard creation 
  - Planned future expansion into feature-specific agents

## Memory Management

- Always remember to update the memory bank at @cc_docs/memory_bank/

## CLI Guidance

- Do not execute python commands in your bash. I am using a python venv on a seperate terminal instance to execute python commands.