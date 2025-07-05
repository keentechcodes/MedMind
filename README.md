# MedMind

**AI-Powered Medical Education Assistant**

A comprehensive AI-powered medical education platform designed specifically for physiology learning. MedMind features a **multi-agent architecture with PydanticAI** that provides personalized, adaptive learning experiences including intelligent tutoring, progress tracking, and contextual question answering for medical students.

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

## 🚀 Features

- **🤖 Multi-Agent Architecture**: PydanticAI-powered Coordinator Agent with specialized learning agents
- **🧠 Intelligent Tutoring**: Context-aware explanations with medical document integration
- **📊 Learning Analytics**: User profiles, progress tracking, and adaptive difficulty adjustment
- **📄 Advanced PDF Processing**: Convert physiology PDFs with enhanced metadata extraction
- **🔍 Smart RAG System**: Metadata-aware chunking with semantic search and retrieval
- **💾 Vector Database**: ChromaDB with Google Gemini embeddings for accurate content retrieval
- **💬 Interactive Interfaces**: Both CLI and Streamlit web interfaces for learning
- **🔧 Type-Safe Operations**: Comprehensive Pydantic models for validated agent interactions

## 🏗️ Architecture

MedMind implements a **multi-agent architecture** with specialized AI agents coordinating to provide comprehensive learning experiences:

```mermaid
graph TD
    User[Medical Student] --> Coordinator[Coordinator Agent]
    Coordinator --> Quiz[Quiz Agent]
    Coordinator --> Progress[Progress Agent] 
    Coordinator --> Tutor[Tutor Agent]
    Coordinator --> Validation[Validation Agent]
    
    Quiz --> RAG[RAG System]
    Tutor --> RAG
    Validation --> Medical_DB[Medical Databases]
    Progress --> Learning_DB[Learning Analytics DB]
    
    RAG --> Vector[ChromaDB Vector Database]
    Vector --> Docs[Processed Medical Documents]
```

### Core Components

- **Coordinator Agent**: Main orchestrator that routes requests and coordinates responses
- **Medical Context System**: User profiles, learning analytics, and session management  
- **RAG Foundation**: PDF processing, intelligent chunking, and vector search
- **Type-Safe Operations**: Pydantic models for validated agent interactions
- **CLI & Web Interfaces**: Interactive testing and learning environments

## 📦 Installation

### Prerequisites

- Python 3.12 or higher
- [uv](https://github.com/astral-sh/uv) package manager
- Google Gemini API key ([Get one here](https://ai.google.dev/))

### Quick Install with uv (Recommended)

```bash
# Clone the repository
git clone https://github.com/keentechcodes/MedMind.git
cd MedMind

# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install dependencies
uv sync

# Activate the environment
source .venv/bin/activate  # On Unix/MacOS
# or
.venv\Scripts\activate     # On Windows
```

### Alternative: Traditional pip Install

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Unix/MacOS

# Install the package
pip install -e .

# Or install with development dependencies
pip install -e .[dev]
```

### Development Setup with uv

```bash
# Install with development dependencies
uv sync --dev

# Install pre-commit hooks
uv run pre-commit install

# Run development tools
uv run black physiology_rag/
uv run pytest
uv run mypy physiology_rag/
```

## ⚙️ Configuration

### Environment Setup

1. Copy the environment template:
```bash
cp .env.example .env
```

2. Edit `.env` with your configuration:
```bash
# Required: Your Google Gemini API key
GEMINI_API_KEY=your-gemini-api-key-here

# Optional: Override default settings
GEMINI_MODEL_NAME=gemini-2.0-flash-exp
CHUNK_SIZE=1000
LOG_LEVEL=INFO
```

### Configuration Options

| Variable | Default | Description |
|----------|---------|-------------|
| `GEMINI_API_KEY` | **Required** | Google Gemini API key |
| `GEMINI_MODEL_NAME` | `gemini-2.0-flash-exp` | Model for response generation |
| `GEMINI_EMBEDDING_MODEL` | `models/text-embedding-004` | Model for embeddings |
| `VECTOR_DB_PATH` | `./data/vector_db` | ChromaDB storage path |
| `CHUNK_SIZE` | `1000` | Maximum chunk size for processing |
| `MAX_CONTEXT_LENGTH` | `3000` | Maximum context for AI responses |
| `LOG_LEVEL` | `INFO` | Logging level |

## 🚀 Quick Start

### 1. Process Your First Document

```bash
# Place your PDF in the data/raw/ directory
cp your-physiology-document.pdf data/raw/

# Convert PDF to markdown (requires marker-pdf setup)
uv run python -m physiology_rag.pdf_processing.converter data/raw/your-document.pdf

# Process documents into chunks
uv run rag-process

# Create vector embeddings
uv run rag-embed
```

### 2. Try the Agent System

```bash
# Interactive CLI with Coordinator Agent
uv run python -m physiology_rag.agents.cli
# or
uv run medmind-cli

# Or launch the Streamlit web interface
uv run streamlit run physiology_rag/ui/streamlit_app.py
```

Try asking questions like:
- "Explain how synaptic transmission works"
- "What are the parts of the motor cortex?"
- "Quiz me on neurophysiology" (shows agent capabilities)

### 3. Command Line Usage

```bash
# Test the agent system
uv run python -c "
import asyncio
from physiology_rag.agents.cli import test_coordinator
asyncio.run(test_coordinator())
"

# Test the RAG system
uv run rag-test

# Process documents only
uv run rag-process

# Create embeddings only  
uv run rag-embed
```

## 📚 Usage Examples

### Agent API

```python
from physiology_rag.agents.coordinator import create_coordinator_agent
from physiology_rag.core.rag_system import RAGSystem

# Initialize the agent system
rag_system = RAGSystem()
coordinator, context = create_coordinator_agent(rag_system, user_id="student123")

# Ask questions through the agent
response = await coordinator.handle_conversation(
    "Explain synaptic transmission", 
    context
)
print(response)
```

### RAG System API

```python
from physiology_rag.core.rag_system import RAGSystem

# Direct RAG usage
rag = RAGSystem()
result = rag.answer_question("What is the cerebral cortex?")

print(result['answer'])
for source in result['sources']:
    print(f"Source: {source['metadata']['document_name']}")
```

### Document Processing

```python
from physiology_rag.core.document_processor import DocumentProcessor

# Process documents
processor = DocumentProcessor()
documents = processor.process_all_documents()

# Save processed data
processor.save_processed_documents(documents)
```

### Vector Database Operations

```python
from physiology_rag.core.embeddings_service import EmbeddingsService

# Initialize service
embeddings = EmbeddingsService()

# Search documents
results = embeddings.search_documents("blood brain barrier")

# Get database stats
stats = embeddings.get_collection_stats()
```

## 🧪 Testing

```bash
# Run all tests
uv run pytest

# Test the agent system specifically
uv run pytest tests/test_agents/test_coordinator.py -v

# Run tests with coverage
uv run pytest --cov=physiology_rag

# Test specific components
uv run pytest tests/test_rag_system.py

# Run tests with detailed output
uv run pytest -v --cov-report=html
```

## 📖 Documentation

- [Setup Guide](docs/setup.md) - Detailed installation and configuration
- [User Guide](docs/user_guide.md) - How to use the system
- [API Documentation](docs/api.md) - Python API reference
- [Development Guide](docs/development.md) - Contributing and development

## 🔧 Development

### Project Structure

```
MedMind/
├── physiology_rag/           # Main package (MedMind core)
│   ├── agents/              # ✅ PydanticAI agent implementations
│   ├── dependencies/        # ✅ Shared context and medical data
│   ├── models/              # ✅ Type-safe Pydantic models
│   ├── config/              # Configuration management
│   ├── core/                # Core RAG system logic
│   ├── pdf_processing/      # PDF conversion
│   ├── ui/                  # User interfaces
│   └── utils/               # Utility functions
├── data/                    # Data storage
│   ├── raw/                 # Input PDFs
│   ├── processed/           # Processed documents
│   ├── vector_db/           # ChromaDB storage
│   └── uploads/             # User uploads
├── tests/                   # Test suite
│   └── test_agents/         # ✅ Agent integration tests
├── docs/                    # Documentation
└── examples/                # Usage examples
```

### Code Quality

The project uses:
- **Black** for code formatting
- **isort** for import sorting
- **mypy** for type checking
- **pytest** for testing
- **pre-commit** for Git hooks

```bash
# Format code
uv run black physiology_rag/

# Sort imports
uv run isort physiology_rag/

# Type checking
uv run mypy physiology_rag/

# Run all quality checks
uv run pre-commit run --all-files

# Lint code
uv run flake8 physiology_rag/
```

## 🚦 System Status

Current implementation status:

✅ **PDF Processing**: Enhanced with Gemini AI  
✅ **Document Processing**: Metadata-aware chunking  
✅ **Vector Database**: ChromaDB with embeddings  
✅ **RAG System**: Complete Q&A pipeline  
✅ **Coordinator Agent**: PydanticAI foundation with working CLI
✅ **Medical Context**: User profiles and learning analytics
✅ **Type Safety**: Comprehensive Pydantic models
✅ **Testing**: Agent test suite (13/14 tests passing)
✅ **Configuration**: Environment-based settings  
🔄 **Specialized Agents**: Quiz, Progress, Tutor, Validation (foundation ready)
🔄 **UI Integration**: Connect agents to Streamlit interface  

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and quality checks
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- 📚 [Documentation](docs/)
- 🐛 [Bug Reports](https://github.com/keentechcodes/MedMind/issues)
- 💬 [Discussions](https://github.com/keentechcodes/MedMind/discussions)

## 🙏 Acknowledgments

- [Marker-PDF](https://github.com/VikParuchuri/marker) for PDF processing
- [Google Gemini](https://ai.google.dev/) for AI capabilities
- [ChromaDB](https://www.trychroma.com/) for vector database
- [Streamlit](https://streamlit.io/) for the web interface

---

**MedMind** - Empowering medical students with AI-powered learning

Built with ❤️ for medical education