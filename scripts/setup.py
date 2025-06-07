#!/usr/bin/env python3
"""
Setup script for the Physiology RAG system.
Orchestrates the complete pipeline from PDF processing to vector database creation.
"""

import click
import json
from pathlib import Path

from physiology_rag.core.document_processor import DocumentProcessor
from physiology_rag.core.embeddings_service import EmbeddingsService
from physiology_rag.utils.logging import setup_logging
from physiology_rag.config.settings import get_settings

logger = setup_logging("setup")


@click.command()
@click.option('--input-dir', '-i', 
              help='Directory containing processed PDFs (default: from settings)')
@click.option('--force', '-f', is_flag=True, 
              help='Force regeneration of embeddings even if they exist')
@click.option('--batch-size', '-b', type=int, default=10,
              help='Batch size for embedding generation')
def main(input_dir, force, batch_size):
    """
    Complete end-to-end setup of the Physiology RAG system.
    
    This script:
    1. Processes documents into chunks
    2. Generates embeddings
    3. Creates vector database
    4. Validates the system
    """
    settings = get_settings()
    
    logger.info("Starting Physiology RAG system setup")
    
    # Step 1: Process documents
    logger.info("Step 1: Processing documents")
    processor = DocumentProcessor(input_dir)
    documents = processor.process_all_documents()
    
    if not documents:
        logger.error("No documents found to process")
        return
    
    # Save processed documents
    processed_file = Path(settings.processed_data_dir) / "processed_documents.json"
    processor.save_processed_documents(documents, str(processed_file))
    
    total_chunks = sum(doc['total_chunks'] for doc in documents)
    logger.info(f"Processed {len(documents)} documents with {total_chunks} chunks")
    
    # Step 2: Generate embeddings and create vector database
    logger.info("Step 2: Creating vector database")
    embeddings_service = EmbeddingsService()
    
    # Check if we need to regenerate embeddings
    stats = embeddings_service.get_collection_stats()
    if stats.get('total_chunks', 0) > 0 and not force:
        logger.info(f"Vector database already exists with {stats['total_chunks']} chunks")
        if not click.confirm("Regenerate embeddings?"):
            logger.info("Skipping embedding generation")
        else:
            embeddings_service.reset_collection()
            embeddings_service.add_documents_to_vector_db(documents)
    else:
        if force and stats.get('total_chunks', 0) > 0:
            logger.info("Force flag set, regenerating embeddings")
            embeddings_service.reset_collection()
        
        embeddings_service.add_documents_to_vector_db(documents)
    
    # Step 3: Validate system
    logger.info("Step 3: Validating system")
    
    # Test retrieval
    test_query = "What is the cerebral cortex?"
    results = embeddings_service.search_documents(test_query, n_results=3)
    
    if results.get('results'):
        logger.info(f"✓ Retrieval test passed: found {len(results['results'])} relevant chunks")
    else:
        logger.error("✗ Retrieval test failed: no results found")
        return
    
    # Test RAG system
    try:
        from physiology_rag.core.rag_system import RAGSystem
        rag = RAGSystem()
        rag_result = rag.answer_question(test_query)
        
        if rag_result.get('answer') and not rag_result['answer'].startswith('Error'):
            logger.info("✓ RAG system test passed")
        else:
            logger.error("✗ RAG system test failed")
            return
            
    except Exception as e:
        logger.error(f"✗ RAG system test failed: {e}")
        return
    
    # Show final stats
    final_stats = embeddings_service.get_collection_stats()
    logger.info("Setup completed successfully!")
    logger.info(f"System ready with {final_stats['total_chunks']} document chunks")
    
    print("\n" + "="*60)
    print("🎉 PHYSIOLOGY RAG SYSTEM SETUP COMPLETE!")
    print("="*60)
    print(f"📚 Documents processed: {len(documents)}")
    print(f"📝 Total chunks: {final_stats['total_chunks']}")
    print(f"🗃️  Vector database: {final_stats['vector_db_path']}")
    print("\nNext steps:")
    print("1. Start the Streamlit app: streamlit run physiology_rag/ui/streamlit_app.py")
    print("2. Or test the CLI: rag-test")
    print("3. Check the documentation: docs/user_guide.md")


if __name__ == "__main__":
    main()