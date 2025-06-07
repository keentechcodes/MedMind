# Technical Context: Technologies & Setup

## Core Technologies

### AI/ML Stack
- **Google Gemini API**: Text embeddings (`text-embedding-004`) and response generation (`gemini-2.0-flash-exp`)
- **ChromaDB**: Vector database with cosine similarity search
- **marker-pdf**: PDF-to-markdown conversion with AI enhancement

### Python Stack
- **Python 3.8+**: Core runtime
- **Pydantic**: Type-safe configuration management
- **Streamlit**: Web UI framework
- **pathlib**: Modern file path handling

### Development Tools
- **pyproject.toml**: Modern Python packaging
- **pytest**: Testing framework
- **black/isort**: Code formatting
- **mypy**: Type checking

## Development Setup

### Prerequisites
1. Python 3.8+ installed
2. Google Gemini API key from ai.google.dev

### Quick Setup
```bash
# Clone and install
pip install -e .

# Configure environment
cp .env.example .env
# Edit .env with GEMINI_API_KEY

# One-command setup
python scripts/setup.py
```

### CLI Commands
- `rag-process`: Process documents into chunks
- `rag-embed`: Create vector embeddings
- `rag-test`: Test RAG pipeline
- `pytest`: Run test suite

## Technical Constraints

### API Limitations
- **Gemini API**: Rate limits, text length restrictions (1000 chars for embeddings)
- **Context Length**: Maximum 3000 characters for RAG context
- **Batch Processing**: 10 embeddings per batch to avoid timeouts

### Performance Considerations
- **Embedding Generation**: Batched processing for efficiency
- **Memory Usage**: ChromaDB persistent storage to avoid reprocessing
- **Response Time**: Limited retrieval results (3 max) for faster responses

## Dependencies

### Core Runtime
```
google-generativeai>=0.3.0
chromadb>=0.4.0
streamlit>=1.28.0
pydantic>=2.0.0
```

### Development
```
pytest>=7.0.0
black>=23.0.0
isort>=5.12.0
mypy>=1.0.0
```

## File Structure Patterns

### Data Organization
- `data/raw/`: Input PDFs
- `data/processed/`: Markdown output + metadata
- `data/vector_db/`: ChromaDB persistent storage
- `data/uploads/`: User file uploads

### Code Organization
- Production code: `physiology_rag/` package
- Examples/debugging: `examples/` directory
- Tests: `tests/` directory
- Documentation: Root-level markdown files

## Tool Usage Patterns

### Environment Management
- `.env` file for local development
- Environment variables for production deployment
- Settings validation on startup

### Testing Strategy
- Unit tests for individual components
- Integration tests for full pipeline
- Example scripts for debugging