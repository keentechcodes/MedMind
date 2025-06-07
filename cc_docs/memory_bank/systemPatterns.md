# System Patterns: Architecture & Design

## Four-Stage Pipeline Architecture

```
PDFs → marker-pdf+Gemini → Markdown+Images → DocumentProcessor → Chunks → EmbeddingsService → ChromaDB → RAGSystem → Streamlit UI
```

## Package Structure Pattern

```
physiology_rag/
├── config/          # Environment-based configuration
├── core/            # Business logic (document_processor, embeddings_service, rag_system)
├── pdf_processing/  # PDF conversion (future)
├── ui/              # Streamlit interface
├── agents/          # Future AI agents
└── utils/           # Logging and utilities
```

## Key Design Patterns

### 1. Configuration Management
- **Pattern**: Centralized settings with environment overrides
- **Implementation**: `physiology_rag/config/settings.py` with Pydantic
- **Usage**: `get_settings()` function provides type-safe configuration

### 2. Logging Pattern
- **Pattern**: Structured logging throughout all modules
- **Implementation**: `physiology_rag/utils/logging.py` with get_logger()
- **Usage**: Each module gets named logger for traceability

### 3. Service Layer Pattern
- **EmbeddingsService**: Handles Gemini API + ChromaDB operations
- **DocumentProcessor**: Manages document chunking and metadata
- **RAGSystem**: Orchestrates retrieval + generation pipeline

### 4. Data Flow Pattern
- **Input**: PDFs in `data/raw/`
- **Processing**: Metadata-aware chunking preserves document structure
- **Storage**: Structured output in `data/processed/`, vectors in `data/vector_db/`
- **Retrieval**: Context-aware search with relevance scoring

## Critical Implementation Paths

### Document Processing
1. Load markdown + metadata from marker-pdf output
2. Use table_of_contents for intelligent section-based chunking
3. Fallback to sentence-based chunking if no metadata
4. Preserve document structure and context

### Vector Database Operations
1. Generate embeddings using `text-embedding-004` model
2. Store in ChromaDB with enhanced metadata
3. Search with cosine similarity
4. Return results with relevance scores

### RAG Pipeline
1. Retrieve top-k relevant chunks (limit 3 for performance)
2. Format context with source attribution
3. Generate response using Gemini 2.0 Flash
4. Return structured result with sources and metadata

## Error Handling Patterns

- **Graceful Degradation**: System continues with reduced functionality on errors
- **Comprehensive Logging**: All errors logged with context
- **User-Friendly Messages**: Technical errors translated for end users
- **Environment Validation**: Early validation of API keys and configuration