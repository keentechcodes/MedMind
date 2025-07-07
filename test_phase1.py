#!/usr/bin/env python3
"""
Manual testing script for Phase 1 enhancements.
Run individual tests by calling the functions directly.
"""

import asyncio
import time
import os
from pathlib import Path

def test_advanced_chunking():
    """Test the new semantic chunking with medical concept detection."""
    print("=== Testing Advanced Chunking ===")
    
    try:
        from physiology_rag.core.advanced_chunking import AdvancedDocumentProcessor
        
        processor = AdvancedDocumentProcessor(chunk_size=800, overlap_ratio=0.15)
        
        # Test medical text
        sample_text = """
        The cerebral cortex is the outermost layer of the brain, composed of gray matter containing neuronal cell bodies. 
        It plays a crucial role in higher-order brain functions such as cognition, memory, and consciousness.
        
        The cortex is divided into four main lobes: frontal, parietal, temporal, and occipital. Each lobe has specific functions.
        The frontal lobe is responsible for executive functions, decision-making, and motor control.
        
        Neurons in the cerebral cortex communicate through synapses, forming complex neural networks.
        Action potentials travel along axons, transmitting electrical signals between neurons.
        Neurotransmitters are released at synapses to facilitate communication.
        
        The blood-brain barrier protects the brain from harmful substances while allowing essential nutrients to pass through.
        This selective permeability is crucial for maintaining brain homeostasis and proper neuronal function.
        """
        
        chunks = processor.process_document_with_advanced_chunking(
            sample_text, 
            metadata={'title': 'Cerebral Cortex Overview', 'page_id': 1}
        )
        
        print(f"✅ Created {len(chunks)} advanced chunks:")
        for i, chunk in enumerate(chunks):
            print(f"\n--- Chunk {i+1} ---")
            print(f"Size: {chunk['size']} characters")
            print(f"Medical concepts: {chunk['medical_concepts']}")
            print(f"Concept density: {chunk['concept_density']:.2f}")
            print(f"Readability: {chunk['readability_score']:.2f}")
            print(f"Overlaps: prev={chunk.get('overlap_previous', False)}, next={chunk.get('overlap_next', False)}")
            print(f"Text preview: {chunk['text'][:100]}...")
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
    except Exception as e:
        print(f"❌ Error testing chunking: {e}")


def test_caching():
    """Test the multi-layer caching system."""
    print("\n=== Testing Caching Layer ===")
    
    try:
        from physiology_rag.core.cache_manager import get_cache_manager
        
        cache_mgr = get_cache_manager()
        
        # Test embedding cache
        print("Testing embedding cache...")
        test_text = "The cerebral cortex is responsible for higher-order thinking."
        test_embedding = [0.1, 0.2, 0.3, 0.4, 0.5] * 150  # 768-dim vector
        
        # Time the set operation
        start = time.time()
        cache_mgr.set_embedding(test_text, test_embedding)
        set_time = time.time() - start
        print(f"✅ Cache set time: {set_time:.4f}s")
        
        # Time the get operation
        start = time.time()
        cached_embedding = cache_mgr.get_embedding(test_text)
        get_time = time.time() - start
        print(f"✅ Cache get time: {get_time:.4f}s")
        print(f"✅ Cache hit: {cached_embedding is not None}")
        print(f"✅ Embeddings match: {cached_embedding == test_embedding}")
        
        # Test query cache
        print("\nTesting query cache...")
        test_query = "What is the cerebral cortex?"
        test_result = {"answer": "The cerebral cortex is...", "sources": []}
        
        cache_mgr.set_query_result(test_query, test_result)
        cached_result = cache_mgr.get_query_result(test_query)
        print(f"✅ Query cache hit: {cached_result is not None}")
        print(f"✅ Results match: {cached_result == test_result}")
        
        # Show comprehensive stats
        stats = cache_mgr.get_comprehensive_stats()
        print(f"\n📊 Cache statistics:")
        print(f"Embedding cache entries: {stats['embedding_cache']['memory_cache']['entries']}")
        print(f"Embedding cache hit rate: {stats['embedding_cache']['memory_cache']['hit_rate']:.2f}")
        print(f"Query cache entries: {stats['query_cache']['entries']}")
        print(f"Query cache hit rate: {stats['query_cache']['hit_rate']:.2f}")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
    except Exception as e:
        print(f"❌ Error testing caching: {e}")


async def test_async_embeddings():
    """Test the new async embedding generation."""
    print("\n=== Testing Async Embeddings ===")
    
    try:
        from physiology_rag.core.async_embeddings import AsyncEmbeddingsService
        
        async with AsyncEmbeddingsService(max_workers=2) as async_service:
            # Test single embedding
            print("Testing single embedding generation...")
            test_text = "The cerebral cortex is responsible for higher-order thinking."
            
            start = time.time()
            embedding = await async_service.generate_single_embedding(test_text)
            single_time = time.time() - start
            
            if embedding:
                print(f"✅ Single embedding: {len(embedding)} dimensions in {single_time:.2f}s")
            else:
                print("❌ Failed to generate single embedding")
            
            # Test batch embeddings
            print("\nTesting batch embedding generation...")
            test_texts = [
                "Neurons communicate through synapses.",
                "The heart pumps blood through the circulatory system.",
                "Homeostasis maintains internal balance.",
                "Action potentials are electrical signals in neurons.",
                "The blood-brain barrier protects neural tissue."
            ]
            
            start = time.time()
            embeddings = await async_service.generate_batch_embeddings(test_texts)
            batch_time = time.time() - start
            
            print(f"✅ Batch embeddings: {len(embeddings)} vectors in {batch_time:.2f}s")
            print(f"✅ Average time per embedding: {batch_time/len(embeddings):.3f}s")
            
            # Show cache performance
            cache_stats = async_service.cache_manager.get_comprehensive_stats()
            print(f"\n📊 Cache performance:")
            print(f"Hit rate: {cache_stats['embedding_cache']['memory_cache']['hit_rate']:.2f}")
            print(f"Total entries: {cache_stats['embedding_cache']['memory_cache']['entries']}")
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
    except Exception as e:
        print(f"❌ Error testing async embeddings: {e}")
        print("Make sure GEMINI_API_KEY is set in your environment")


def test_enhanced_processing():
    """Test the updated document processor with advanced chunking."""
    print("\n=== Testing Enhanced Document Processing ===")
    
    try:
        from physiology_rag.core.document_processor import DocumentProcessor
        
        # Test with advanced chunking enabled (default)
        processor = DocumentProcessor(use_advanced_chunking=True)
        
        # Check if any documents exist
        data_dir = Path("./data/processed")
        if not data_dir.exists():
            print(f"❌ Data directory not found: {data_dir}")
            print("Please ensure you have processed documents in ./data/processed/")
            return
        
        doc_dirs = [d for d in data_dir.iterdir() if d.is_dir()]
        if not doc_dirs:
            print(f"❌ No document directories found in {data_dir}")
            print("Please run document processing first.")
            return
        
        # Test processing first available document
        test_doc = doc_dirs[0].name
        print(f"Testing with document: {test_doc}")
        
        result = processor.process_document(test_doc)
        
        print(f"✅ Processed document: {result['document_name']}")
        print(f"✅ Total chunks: {result['total_chunks']}")
        print(f"✅ Total images: {result['total_images']}")
        
        # Analyze chunk types and features
        chunk_types = {}
        advanced_features = 0
        
        for chunk in result['chunks']:
            chunk_type = chunk.get('type', 'unknown')
            chunk_types[chunk_type] = chunk_types.get(chunk_type, 0) + 1
            
            # Check for advanced features
            if 'medical_concepts' in chunk:
                advanced_features += 1
        
        print(f"\n📊 Chunk analysis:")
        for chunk_type, count in chunk_types.items():
            print(f"  {chunk_type}: {count} chunks")
        
        print(f"✅ Chunks with advanced features: {advanced_features}/{len(result['chunks'])}")
        
        # Show sample advanced chunk
        if advanced_features > 0:
            for chunk in result['chunks']:
                if 'medical_concepts' in chunk:
                    print(f"\n🔬 Sample advanced chunk:")
                    print(f"  Medical concepts: {chunk['medical_concepts']}")
                    print(f"  Concept density: {chunk.get('concept_density', 'N/A')}")
                    print(f"  Readability: {chunk.get('readability_score', 'N/A')}")
                    break
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
    except Exception as e:
        print(f"❌ Error processing document: {e}")


def test_enhanced_rag():
    """Test how the enhancements integrate with the existing RAG pipeline."""
    print("\n=== Testing Enhanced RAG System Integration ===")
    
    try:
        from physiology_rag.core.rag_system import RAGSystem
        from physiology_rag.core.cache_manager import get_cache_manager
        
        # Initialize RAG system (should use enhanced components)
        rag = RAGSystem()
        cache_mgr = get_cache_manager()
        
        # Test queries with timing
        test_queries = [
            "What is the cerebral cortex?",
            "How do neurons communicate?",
            "What is the blood-brain barrier?"
        ]
        
        for i, query in enumerate(test_queries):
            print(f"\n--- Query {i+1}: {query} ---")
            
            # First run (should populate cache)
            start = time.time()
            result = rag.answer_question(query)
            first_time = time.time() - start
            
            print(f"✅ First run: {first_time:.2f}s")
            print(f"✅ Sources: {len(result.get('sources', []))}")
            print(f"✅ Answer preview: {result.get('answer', '')[:100]}...")
            
            # Second run (should use cache)
            start = time.time()
            result2 = rag.answer_question(query)
            second_time = time.time() - start
            
            print(f"✅ Second run: {second_time:.2f}s")
            if second_time > 0:
                print(f"🚀 Speedup: {first_time/second_time:.1f}x")
        
        # Show final cache stats
        stats = cache_mgr.get_comprehensive_stats()
        print(f"\n📊 Final cache statistics:")
        print(f"Embedding cache hit rate: {stats['embedding_cache']['memory_cache']['hit_rate']:.2f}")
        print(f"Query cache hit rate: {stats['query_cache']['hit_rate']:.2f}")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
    except Exception as e:
        print(f"❌ Error testing RAG system: {e}")
        print("Make sure GEMINI_API_KEY is set and documents are processed.")


def test_system_health():
    """Check overall system health and configuration."""
    print("\n=== System Health Check ===")
    
    # Check configuration
    print("\n1. Configuration:")
    try:
        from physiology_rag.config.settings import get_settings
        settings = get_settings()
        print(f"✅ Settings loaded successfully")
        print(f"   Chunk size: {settings.chunk_size}")
        print(f"   Max context length: {settings.max_context_length}")
        print(f"   Batch size: {settings.batch_size}")
        print(f"   Vector DB path: {settings.vector_db_path}")
    except Exception as e:
        print(f"❌ Settings error: {e}")
    
    # Check API key
    print("\n2. API Configuration:")
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        print(f"✅ GEMINI_API_KEY is set ({len(api_key)} chars)")
    else:
        print("❌ GEMINI_API_KEY not set")
    
    # Check data directories
    print("\n3. Data Directories:")
    data_paths = [
        "./data/processed",
        "./data/vector_db",
        "./data/cache"
    ]
    
    for path in data_paths:
        p = Path(path)
        if p.exists():
            items = len(list(p.iterdir())) if p.is_dir() else 0
            print(f"✅ {path} exists ({items} items)")
        else:
            print(f"❌ {path} missing")
    
    # Check embeddings service
    print("\n4. Embeddings Service:")
    try:
        from physiology_rag.core.embeddings_service import EmbeddingsService
        embeddings_service = EmbeddingsService()
        stats = embeddings_service.get_collection_stats()
        print(f"✅ Vector database connected")
        print(f"   Total chunks: {stats.get('total_chunks', 'Unknown')}")
        print(f"   Collection: {stats.get('collection_name', 'Unknown')}")
    except Exception as e:
        print(f"❌ Embeddings service error: {e}")


async def benchmark_performance():
    """Quick performance benchmark."""
    print("\n=== Performance Benchmark ===")
    
    # Test data
    test_texts = [
        "The cerebral cortex processes information.",
        "Neurons transmit electrical signals.",
        "The heart circulates blood throughout the body.",
        "Lungs facilitate gas exchange.",
        "The kidney filters blood and produces urine."
    ] * 2  # 10 texts total
    
    try:
        from physiology_rag.core.embeddings_service import EmbeddingsService
        from physiology_rag.core.async_embeddings import AsyncEmbeddingsService
        
        # Test traditional synchronous embeddings
        print("\n1. Traditional Sync Embeddings:")
        sync_service = EmbeddingsService()
        
        start = time.time()
        sync_embeddings = sync_service.generate_embeddings(test_texts, batch_size=5)
        sync_time = time.time() - start
        
        print(f"   Time: {sync_time:.2f}s")
        print(f"   Embeddings: {len(sync_embeddings)}")
        print(f"   Avg per embedding: {sync_time/len(sync_embeddings):.3f}s")
        
        # Test async embeddings
        print("\n2. Async Embeddings:")
        async with AsyncEmbeddingsService(max_workers=2) as async_service:
            start = time.time()
            async_embeddings = await async_service.generate_batch_embeddings(test_texts, batch_size=5)
            async_time = time.time() - start
            
            print(f"   Time: {async_time:.2f}s")
            print(f"   Embeddings: {len(async_embeddings)}")
            print(f"   Avg per embedding: {async_time/len(async_embeddings):.3f}s")
            if async_time > 0:
                print(f"   🚀 Speedup: {sync_time/async_time:.1f}x")
            
            # Test cache performance
            print("\n3. Cache Performance:")
            start = time.time()
            cached_embeddings = await async_service.generate_batch_embeddings(test_texts[:3])
            cache_time = time.time() - start
            
            print(f"   Cached retrieval time: {cache_time:.3f}s")
            if cache_time > 0:
                expected_time = async_time/len(async_embeddings)*3
                print(f"   🚀 Cache speedup: {expected_time/cache_time:.1f}x")
    
    except Exception as e:
        print(f"❌ Benchmark error: {e}")
        print("Make sure GEMINI_API_KEY is set")


def main():
    """Run all tests or specific ones."""
    print("🧠 MedMind Phase 1 Enhancement Testing")
    print("=====================================")
    
    # Run tests in order
    test_system_health()
    test_advanced_chunking()
    test_caching()
    
    # Async tests
    print("\n⏳ Running async tests...")
    asyncio.run(test_async_embeddings())
    
    # Integration tests
    test_enhanced_processing()
    test_enhanced_rag()
    
    # Performance tests
    print("\n⏳ Running performance benchmark...")
    asyncio.run(benchmark_performance())
    
    print("\n✅ Testing complete!")


if __name__ == "__main__":
    main()