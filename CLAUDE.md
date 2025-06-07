# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a professionally structured PDF-to-Markdown conversion and RAG (Retrieval-Augmented Generation) system designed specifically for physiology lecture documents. The system converts PDFs to markdown, processes them into searchable chunks, and enables AI-powered question answering for medical students.

**🏗️ RESTRUCTURED PROJECT**: Now follows Python best practices with proper package structure, configuration management, and comprehensive documentation.

## Architecture

The codebase follows a four-stage pipeline:

1. **PDF Conversion**: Uses marker-pdf library with Google Gemini AI to convert PDFs to structured markdown with extracted images
2. **Document Processing**: Chunks markdown content intelligently using metadata table-of-contents for optimal retrieval 
3. **Vector Database**: Uses Google Gemini API embeddings and ChromaDB for semantic search and retrieval
4. **RAG Interface**: Complete question-answering system with Streamlit chat interface

### Core Components

**Structured Package Layout:**
- `physiology_rag/config/`: Configuration management with environment variables
- `physiology_rag/core/`: Core business logic (document processing, embeddings, RAG)
- `physiology_rag/pdf_processing/`: PDF conversion using marker-pdf with Gemini AI
- `physiology_rag/ui/`: Streamlit chat interface
- `physiology_rag/agents/`: Future AI agents (quiz, flashcard makers)
- `physiology_rag/utils/`: Logging and utility functions

**Key Features:**
- ✅ **Environment-based Configuration**: No hardcoded API keys
- ✅ **Comprehensive Logging**: Structured logging throughout
- ✅ **Professional Documentation**: README, setup guides, API docs
- ✅ **Testing Framework**: pytest with fixtures and coverage
- ✅ **Modern Packaging**: pyproject.toml with proper dependencies

### Data Flow

1. PDFs (`data/raw/`) → marker-pdf converter → Markdown + Images + Metadata (`data/processed/`)
2. Markdown → DocumentProcessor → Section-based chunks → `data/processed/processed_documents.json`
3. Chunks → EmbeddingsService → Vector embeddings → ChromaDB (`data/vector_db/`)
4. Query → RAGSystem → Retrieval + Gemini generation → Answer with sources

## Key Commands

### Environment Setup
```bash
# Install the package and dependencies
pip install -e .

# Copy environment template and configure
cp .env.example .env
# Edit .env with your GEMINI_API_KEY

# Development setup (optional)
pip install -e .[dev]
```

### Quick Start
```bash
# Complete system setup (one command!)
python scripts/setup.py

# Launch Streamlit chat interface
streamlit run physiology_rag/ui/streamlit_app.py
```

### Individual Components
```bash
# Process documents only
rag-process

# Create embeddings only
rag-embed

# Test RAG system
rag-test

# Run tests
pytest
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