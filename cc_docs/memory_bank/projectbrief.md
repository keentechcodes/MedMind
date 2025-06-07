# Project Brief: Physiology RAG System

## Core Requirements

**Primary Goal**: Create a professional PDF-to-RAG system for physiology education that converts PDF lecture documents into an AI-powered question-answering system for medical students.

## Key Capabilities

1. **PDF Processing**: Convert physiology PDFs to structured markdown with image extraction using marker-pdf + Gemini AI
2. **Intelligent Chunking**: Process documents into searchable chunks using metadata table-of-contents
3. **Vector Database**: Store embeddings using Google Gemini API + ChromaDB for semantic search
4. **RAG Interface**: Complete question-answering with source attribution via Streamlit chat UI

## Success Criteria

- ✅ Professional Python package structure following best practices
- ✅ Environment-based configuration (no hardcoded API keys)
- ✅ Comprehensive logging and error handling
- ✅ Clean, organized codebase ready for team collaboration
- ✅ Working system that can answer physiology questions with source citations

## Current Status

**COMPLETED**: Full system reorganization from prototype scripts to production-ready package. All core functionality operational with 13 physiology documents processed, 643 chunks created, working vector database, and functional Streamlit interface.

## Scope Boundaries

- Focus on physiology education specifically
- Use Google Gemini API (not OpenAI or other providers)
- Streamlit for UI (not web frameworks)
- ChromaDB for vector storage (not alternatives)
- Target medical students as primary users