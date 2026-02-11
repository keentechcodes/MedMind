# Voyage AI Embeddings & System Refactor Strategy

## Overview

This document summarizes the analysis and strategic plan for migrating from Google Gemini embeddings to Voyage AI embeddings, and broader system refactoring to support new requirements including DeepSeek OCR, LLM agnostic architecture, and medical note validation capabilities.

**Date**: February 12, 2026  
**Status**: Strategic Plan  
**Recommended Approach**: Strategic Refactor (3-4 weeks)

## Current Architecture Analysis

### Existing System Components
- **Document Processing**: Uses `marker-pdf` for PDF-to-markdown conversion
- **Embeddings**: Google Gemini API (`models/text-embedding-004`, 768 dimensions)
- **Vector Database**: ChromaDB with persistent storage
- **LLM Integration**: Google Gemini for response generation
- **Caching**: Multi-level cache for embeddings and API responses
- **API/UI**: FastAPI backend with Streamlit frontend

### Key Files Identified
1. `physiology_rag/core/embeddings_service.py` - Synchronous Gemini embeddings
2. `physiology_rag/core/async_embeddings.py` - Async batch processing
3. `physiology_rag/core/rag_system.py` - RAG pipeline with Gemini
4. `physiology_rag/config/settings.py` - Configuration with Gemini defaults
5. `physiology_rag/core/document_processor.py` - Document chunking with metadata

## New Requirements Analysis

### Technology Stack Updates
1. **DeepSeek OCR** - Replace `marker-pdf` for live PDF-to-markdown conversion with metadata preservation (ToC, hierarchy)
2. **Voyage AI Embeddings** - Replace Google Gemini embeddings
3. **Zeroentropy Reranker** - Add to retrieval pipeline for improved relevance
4. **LLM Agnostic Architecture** - Support GPT, Gemini, Claude, Kimi, DeepSeek interchangeably
5. **Medical Note Validation** - Core new feature: compare trans(medical) notes against lecture slides and textbook

### Critical Technical Constraints
- **Dimension Incompatibility**: Voyage (1024D) ≠ Gemini (768D) → **requires reindexing**
- **Provider Differences**: API parameters, error handling, rate limits vary
- **Cache Collisions**: Same text with different providers yields different embeddings

## Implementation Options

### Option 1: Complete Rebuild (4-6 weeks)
**Pros:**
- Clean architecture with no legacy constraints
- Optimized for new comparison engine
- Unified provider abstraction from start

**Cons:**
- Lose tested components and patterns
- Longer development time
- Higher risk of regressions

### Option 2: Strategic Refactor (3-4 weeks) ✅ **Recommended**
**Pros:**
- Reuse solid existing patterns (configuration, caching, vector DB)
- Gradual migration with fallback options
- Faster time to working prototypes
- Lower risk with incremental changes

**Cons:**
- Some technical debt from adapter patterns
- Need to maintain backward compatibility during transition

## Refined Voyage AI Implementation Plan

### Architecture Principles
1. **Provider Abstraction**: Clean interfaces for embeddings, LLMs, OCR, rerankers
2. **Dimension Awareness**: Provider-specific vector collections
3. **Cache Isolation**: Provider-prefixed cache keys
4. **Gradual Migration**: Parallel collections during transition

### Core Abstraction Layer
```python
# physiology_rag/core/embedding_providers/base.py
class EmbeddingProvider(ABC):
    @abstractmethod
    def generate_embedding(self, text: str, is_query: bool = False) -> List[float]:
        pass
    
    @abstractmethod
    def get_dimensions(self) -> int:
        pass
    
    @abstractmethod
    def get_cache_prefix(self) -> str:
        pass
```

### Provider-Aware Configuration
```python
# Updated settings.py
embedding_provider: str = "gemini"  # "gemini" or "voyage"
voyage_api_key: Optional[str] = None
voyage_model: str = "voyage-4"
voyage_output_dimension: Optional[int] = None  # 256, 512, 1024, 2048

# Provider-aware collection naming
def get_collection_name(self) -> str:
    return f"{settings.collection_name}_{settings.embedding_provider}"
```

## Strategic Refactor Phases

### Phase 1: Foundation Refactor (2-3 weeks)
1. **Week 1**: Create abstract provider interfaces (Embedding, LLM, OCR, Reranker)
2. **Week 2**: Update configuration system for multi-provider support
3. **Week 3**: Refactor document processing with DeepSeek OCR integration

### Phase 2: Core Logic Implementation (1-2 weeks)
1. **Build comparison engine** for medical note validation
2. **Implement Voyage embeddings** with provider pattern
3. **Integrate Zeroentropy reranker** into retrieval pipeline

### Phase 3: Integration & Testing (1 week)
1. Update API/UI for new comparison features
2. Create migration utilities from old to new system
3. Comprehensive testing of all provider combinations

## Critical Implementation Details

### 1. Dimension Management Strategy
```python
# Cannot mix 768D and 1024D embeddings in same collection
# Solution: Provider-specific collections with metadata
collection = client.get_or_create_collection(
    name=f"physiology_documents_voyage",
    metadata={
        "embedding_provider": "voyage",
        "embedding_dimensions": 1024,
        "created_at": datetime.now().isoformat()
    }
)
```

### 2. Migration Requirements
**Yes, reindexing is mandatory** because:
- Voyage AI default embeddings are 1024-dimensional
- Gemini embeddings are 768-dimensional
- Vector similarity requires consistent dimensions

**Migration Script Needed:**
```python
def migrate_gemini_to_voyage():
    # 1. Export existing documents from Gemini collection
    # 2. Create new Voyage collection with metadata
    # 3. Regenerate embeddings with Voyage provider
    # 4. Update application configuration
    # 5. Optional: Keep Gemini collection for A/B testing
```

### 3. New Domain Logic: Medical Note Validator
```python
class MedicalNoteValidator:
    def validate_notes(self, trans_notes: str, lecture_pdf: str, textbook_pdf: str):
        """Compare medical notes against reference materials."""
        # Steps:
        # 1. OCR process both PDFs with DeepSeek (preserving hierarchy)
        # 2. Generate embeddings for all content with Voyage
        # 3. Retrieve relevant sections for each note claim
        # 4. Use LLM (agnostic) to assess accuracy with evidence
        # 5. Generate discrepancy report with confidence scores
```

## Files Requiring Updates

### Keep (With Updates):
- `physiology_rag/config/settings.py` - Add provider configurations
- `physiology_rag/core/cache_manager.py` - Update for provider isolation
- API/UI frameworks - Update interface logic

### Refactor (Major Changes):
- `physiology_rag/core/embeddings_service.py` - Implement provider pattern
- `physiology_rag/core/async_embeddings.py` - Async provider support
- `physiology_rag/core/document_processor.py` - Replace marker-pdf with DeepSeek OCR
- `physiology_rag/core/rag_system.py` - Add reranker and comparison logic

### New Components:
- `physiology_rag/core/embedding_providers/` - Provider abstraction layer
- `physiology_rag/core/llm_providers/` - GPT/Gemini/Claude/Kimi/DeepSeek support
- `physiology_rag/core/ocr_providers/` - DeepSeek OCR integration
- `physiology_rag/core/comparison/` - Medical note validation engine
- `physiology_rag/utils/migration.py` - Migration utilities

## Risk Mitigation Strategy

### High Risk Areas:
1. **Dimension Incompatibility**: Solved with provider-aware collections
2. **Cache Corruption**: Provider-prefixed cache keys
3. **API Differences**: Comprehensive error handling with fallbacks
4. **Migration Downtime**: Parallel collections during transition

### Validation Approach:
1. **Unit Tests**: Provider interfaces and error handling
2. **Integration Tests**: End-to-end RAG pipeline with all providers
3. **Performance Benchmark**: Compare latency, accuracy, cost
4. **A/B Testing**: Parallel runs with same queries across providers

## Success Metrics

1. **Feature Parity**: All existing functionality works with Voyage provider
2. **Performance**: Comparable or better retrieval quality vs Gemini
3. **Accuracy**: Medical note validation produces reliable discrepancy reports
4. **Flexibility**: Seamless switching between LLM/embedding providers
5. **Usability**: Clear configuration and migration documentation

## Immediate Next Steps

1. **Create provider abstraction interfaces** (2-3 days)
2. **Implement DeepSeek OCR prototype** (3-4 days)
3. **Build comparison engine proof-of-concept** (4-5 days)
4. **Then refactor embeddings and LLM providers** (1-2 weeks)

## Conclusion

The **strategic refactor approach** is recommended because it:
- Leverages existing solid architectural patterns
- Allows incremental migration with fallback options
- Provides faster time to working prototypes
- Maintains ability to evolve architecture as requirements change
- Minimizes risk by reusing tested components

This approach balances the need for architectural modernization with practical delivery timelines, enabling validation of the new medical note comparison functionality while systematically upgrading the underlying technology stack.

## Appendix: Technical Details

### Voyage AI Model Options
| Model | Context Length | Dimensions | Description |
|-------|---------------|------------|-------------|
| `voyage-4` | 32,000 tokens | 1024 (default) | General-purpose retrieval |
| `voyage-4-large` | 32,000 tokens | 1024 (default) | Enhanced retrieval quality |
| `voyage-4-lite` | 32,000 tokens | 1024 (default) | Optimized for latency/cost |
| Configurable dimensions: 256, 512, 1024, 2048 |

### Parameter Mapping Guide
| Gemini Parameter | Voyage AI Equivalent |
|-----------------|----------------------|
| `task_type="retrieval_query"` | `input_type="query"` |
| `task_type="retrieval_document"` | `input_type="document"` |
| `batch_size` (settings) | Max 1000 texts per request |
| No explicit token limit | 1M tokens total limit |

### Cache Key Strategy
```python
# Current (collision risk):
cache_key = f"{task_type}:{text_content}"

# New (provider-isolated):
cache_key = f"{provider.get_cache_prefix()}:{task_type}:{text_content}"
# Examples: "gemini:retrieval_document:text", "voyage:query:text"
```

### Migration Checklist
- [ ] Backup existing vector database
- [ ] Export documents with metadata
- [ ] Create Voyage-specific collection
- [ ] Regenerate embeddings with Voyage provider
- [ ] Update configuration settings
- [ ] Test retrieval quality
- [ ] Update cache keys
- [ ] Deploy with fallback option
- [ ] Monitor performance metrics
- [ ] Optional: Delete old collection after validation