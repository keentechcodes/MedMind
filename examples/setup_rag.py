#!/usr/bin/env python3
"""
Setup script for the Physiology RAG Chatbot
Run this script to process documents and set up the vector database.
"""

import os
import json
from physiology_rag.core.document_processor import DocumentProcessor
from physiology_rag.core.embeddings_service import EmbeddingsService

def main():
    print("🧠 Setting up Physiology RAG Chatbot...")
    
    # Check for required environment variables
    project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
    if not project_id:
        print("❌ Error: GOOGLE_CLOUD_PROJECT environment variable not set")
        print("Please set it with: export GOOGLE_CLOUD_PROJECT=your-project-id")
        return
    
    # Step 1: Process documents
    print("\n📄 Processing documents...")
    processor = DocumentProcessor()
    documents = processor.process_all_documents()
    
    # Save processed data
    with open("processed_documents.json", "w", encoding="utf-8") as f:
        json.dump(documents, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Processed {len(documents)} documents")
    
    # Step 2: Set up embeddings and vector database
    print("\n🔗 Setting up embeddings and vector database...")
    embeddings_service = EmbeddingsService(project_id=project_id)
    
    # Add documents to vector database
    embeddings_service.add_documents_to_vector_db(documents)
    
    # Get stats
    stats = embeddings_service.get_collection_stats()
    print(f"✅ Vector database ready with {stats['total_chunks']} chunks")
    
    # Test search
    print("\n🔍 Testing search functionality...")
    test_query = "What is neurophysiology?"
    results = embeddings_service.search_documents(test_query, n_results=3)
    
    print(f"Search results for '{test_query}':")
    for i, result in enumerate(results['results']):
        print(f"  {i+1}. {result['metadata']['document_name']} (Score: {result['similarity_score']:.3f})")
    
    print("\n🎉 Setup complete! You can now run the chatbot.")
    print("Next steps:")
    print("1. Run: python chatbot_app.py")
    print("2. Open your browser to the displayed URL")

if __name__ == "__main__":
    main()